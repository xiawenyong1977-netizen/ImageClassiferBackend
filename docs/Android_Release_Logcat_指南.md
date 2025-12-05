# Android Release 版本日志查看指南

## 📱 使用 adb logcat 查看 Release 版本日志

### 1. 基本命令

```bash
# 查看所有日志
adb logcat

# 清空日志缓冲区并开始查看
adb logcat -c && adb logcat

# 查看并保存到文件
adb logcat > log.txt

# 实时查看并保存到文件
adb logcat | tee log.txt
```

### 2. 过滤特定应用的日志

```bash
# 方法1：使用包名过滤（Windows）
adb logcat | findstr "com.your.package"

# 方法1：使用包名过滤（Linux/Mac）
adb logcat | grep "com.your.package"

# 方法2：使用 PID（先获取应用PID）
adb shell pidof com.your.package
adb logcat --pid=<PID>

# 方法3：使用包名直接过滤
adb logcat | grep -i "your_app_name"
```

### 3. 按日志级别过滤

```bash
# 只显示错误日志
adb logcat *:E

# 显示警告及以上
adb logcat *:W

# 显示信息及以上
adb logcat *:I

# 显示调试及以上
adb logcat *:D

# 显示所有日志
adb logcat *:V
```

### 4. 按标签（TAG）过滤

```bash
# 显示特定标签的日志
adb logcat -s TAG_NAME

# 显示多个标签
adb logcat -s TAG1 TAG2

# 显示特定标签的特定级别
adb logcat TAG_NAME:E *:S
```

### 5. Release 版本的特殊处理

#### 问题：Release 版本默认不输出日志

Release 版本通常因为以下原因看不到日志：
- ProGuard/R8 可能移除了日志代码
- 日志级别被设置为较高（如只显示 ERROR）
- 应用代码中使用了 `if (BuildConfig.DEBUG)` 条件判断

#### 解决方案

**方案1：在代码中保留日志（推荐）**

在 `build.gradle` 中配置 ProGuard 规则：

```gradle
buildTypes {
    release {
        minifyEnabled true
        proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
    }
}
```

在 `proguard-rules.pro` 中添加：

```proguard
# 保留日志相关代码
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
    public static *** w(...);
    public static *** e(...);
}

# 或者不优化日志（更简单）
-keep class android.util.Log { *; }
-dontwarn android.util.Log
```

**方案2：使用条件日志（但保留日志代码）**

```java
public class LogUtil {
    private static final boolean LOG_ENABLED = true; // Release 版本也设为 true
    
    public static void d(String tag, String msg) {
        if (LOG_ENABLED) {
            Log.d(tag, msg);
        }
    }
    
    public static void e(String tag, String msg) {
        if (LOG_ENABLED) {
            Log.e(tag, msg);
        }
    }
}
```

**方案3：使用系统属性控制日志**

```java
// 在应用启动时设置
System.setProperty("log.tag.YourTag", "VERBOSE");

// 或者通过 adb 设置
adb shell setprop log.tag.YourTag VERBOSE
```

### 6. 常用组合命令

```bash
# 查看特定应用的所有日志（Windows）
adb logcat | findstr "com.your.package"

# 查看特定应用的所有日志（Linux/Mac）
adb logcat | grep "com.your.package"

# 查看错误日志并保存
adb logcat *:E > error_log.txt

# 清空日志后查看特定应用
adb logcat -c && adb logcat | findstr "com.your.package"

# 查看特定时间段的日志
adb logcat -t 100  # 显示最近100行
adb logcat -t '01-01 12:00:00.000'  # 从指定时间开始

# 查看并过滤多个条件
adb logcat *:E | findstr "com.your.package"
```

### 7. 高级用法

```bash
# 查看特定进程的日志
adb logcat --pid=$(adb shell pidof com.your.package)

# 查看特定用户ID的日志
adb logcat --uid=$(adb shell dumpsys package com.your.package | grep userId)

# 格式化输出
adb logcat -v time  # 显示时间戳
adb logcat -v threadtime  # 显示线程和时间
adb logcat -v long  # 详细格式
adb logcat -v brief  # 简要格式（默认）

# 组合使用
adb logcat -v time *:E | findstr "com.your.package"
```

### 8. 实时监控和过滤

```bash
# 实时查看并过滤（Windows PowerShell）
adb logcat | Select-String "your_keyword"

# 实时查看并过滤（Linux/Mac）
adb logcat | grep --line-buffered "your_keyword"

# 查看崩溃日志
adb logcat *:E AndroidRuntime:E *:S
```

### 9. 查看系统日志

```bash
# 查看系统事件
adb logcat -b system

# 查看崩溃日志
adb logcat -b crash

# 查看所有缓冲区
adb logcat -b all
```

### 10. 调试技巧

```bash
# 1. 先清空日志，然后复现问题
adb logcat -c
# 执行操作...
adb logcat -d > log.txt  # -d 表示输出后退出

# 2. 查看应用启动日志
adb logcat -c
adb logcat | findstr "com.your.package"
# 然后启动应用

# 3. 查看特定 Activity 的日志
adb logcat | findstr "ActivityManager"

# 4. 查看网络请求日志（如果使用 OkHttp）
adb logcat | findstr "OkHttp"
```

### 11. 常见问题排查

**问题1：看不到任何日志**
- 检查设备是否连接：`adb devices`
- 检查应用是否在运行
- 检查日志级别是否设置过高
- 检查 ProGuard 是否移除了日志代码

**问题2：日志太多，难以查找**
- 使用更精确的过滤条件
- 使用 `-c` 先清空日志
- 使用 `-t` 限制日志行数

**问题3：Release 版本看不到日志**
- 检查 ProGuard 配置
- 确保日志代码没有被优化掉
- 使用 `-assumenosideeffects` 规则保留日志

### 12. 实用脚本示例

**Windows 批处理脚本（view_log.bat）**
```batch
@echo off
echo 正在查看应用日志...
adb logcat -c
adb logcat | findstr "com.your.package"
```

**Linux/Mac Shell 脚本（view_log.sh）**
```bash
#!/bin/bash
echo "正在查看应用日志..."
adb logcat -c
adb logcat | grep "com.your.package"
```

### 13. 推荐的工作流程

1. **清空日志缓冲区**
   ```bash
   adb logcat -c
   ```

2. **开始监控日志**
   ```bash
   adb logcat -v time *:I | findstr "com.your.package"
   ```

3. **复现问题**

4. **停止监控并保存**
   - 按 `Ctrl+C` 停止
   - 或使用 `adb logcat -d > log.txt` 保存

5. **分析日志文件**

---

## 📝 注意事项

1. **性能影响**：Release 版本保留日志可能会略微影响性能
2. **安全考虑**：日志中可能包含敏感信息，发布前要清理
3. **日志级别**：建议 Release 版本只保留 ERROR 和 WARNING 级别
4. **ProGuard 规则**：确保正确配置，避免日志代码被移除

---

**最后更新**: 2024-11-18  
**适用场景**: Android Release 版本调试和问题排查



