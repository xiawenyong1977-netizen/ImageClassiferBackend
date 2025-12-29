/**
 * Cloudflare Worker - Nominatim API 代理
 * 用于转发Nominatim API请求，解决服务器无法访问外网的问题
 * 
 * 部署步骤：
 * 1. 登录 Cloudflare Dashboard
 * 2. 进入 Workers & Pages
 * 3. 创建新的 Worker
 * 4. 复制此代码到 Worker
 * 5. 保存并部署
 * 6. 获取 Worker URL（例如：https://nominatim-proxy.your-subdomain.workers.dev）
 * 7. 在后端配置中使用此 URL
 */

export default {
  async fetch(request, env, ctx) {
    // 只允许 POST 和 GET 请求
    if (request.method !== 'GET' && request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    // 解析请求URL，获取查询参数
    const url = new URL(request.url);
    
    // 如果请求路径是 /reverse，转发到Nominatim API
    if (url.pathname === '/reverse' || url.pathname === '/reverse/') {
      // 构建Nominatim API URL
      const nominatimUrl = new URL('https://nominatim.openstreetmap.org/reverse');
      
      // 复制所有查询参数
      url.searchParams.forEach((value, key) => {
        nominatimUrl.searchParams.append(key, value);
      });
      
      // 准备请求头
      const headers = new Headers();
      headers.set('User-Agent', 'ImageClassifierBackend/1.0');
      headers.set('Accept', 'application/json');
      headers.set('Accept-Language', 'zh-CN,en');
      
      // 添加CORS头（允许跨域请求）
      headers.set('Access-Control-Allow-Origin', '*');
      headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      headers.set('Access-Control-Allow-Headers', 'Content-Type, User-Agent');
      
      // 处理OPTIONS预检请求
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          status: 204,
          headers: headers
        });
      }
      
      try {
        // 转发请求到Nominatim API
        // 注意：Cloudflare Worker免费版超时限制是10秒，付费版是30秒
        // 如果使用免费版，需要设置更短的超时时间
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8秒超时（免费版限制）
        
        const response = await fetch(nominatimUrl.toString(), {
          method: 'GET',
          headers: {
            'User-Agent': 'ImageClassifierBackend/1.0',
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,en'
          },
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        // 检查响应状态
        if (!response.ok) {
          return new Response(
            JSON.stringify({
              error: 'Nominatim API error',
              status: response.status,
              statusText: response.statusText
            }),
            {
              status: response.status,
              headers: {
                'Content-Type': 'application/json',
                ...Object.fromEntries(headers.entries())
              }
            }
          );
        }
        
        // 获取响应数据
        const data = await response.json();
        
        // 返回响应（添加CORS头）
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            ...Object.fromEntries(headers.entries())
          }
        });
        
      } catch (error) {
        // 处理错误
        console.error('Nominatim API proxy error:', error);
        
        // 判断错误类型
        let statusCode = 500;
        let errorMessage = error.message;
        
        if (error.name === 'AbortError' || error.message.includes('timeout') || error.message.includes('aborted')) {
          statusCode = 504; // Gateway Timeout
          errorMessage = 'Nominatim API request timeout (Worker timeout limit: 8s, free tier limit: 10s)';
        } else if (error.message.includes('fetch failed') || error.message.includes('network')) {
          statusCode = 502; // Bad Gateway
          errorMessage = 'Failed to connect to Nominatim API';
        }
        
        return new Response(
          JSON.stringify({
            error: 'Proxy error',
            message: errorMessage,
            type: error.name,
            timestamp: new Date().toISOString()
          }),
          {
            status: statusCode,
            headers: {
              'Content-Type': 'application/json',
              ...Object.fromEntries(headers.entries())
            }
          }
        );
      }
    }
    
    // 如果路径不匹配，返回404
    return new Response('Not found', { status: 404 });
  }
};

