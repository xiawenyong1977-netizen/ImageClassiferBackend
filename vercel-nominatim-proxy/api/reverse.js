/**
 * Vercel Serverless Function - Nominatim API 代理
 * 用于转发Nominatim API请求，解决服务器无法访问外网的问题
 * 
 * 部署步骤：
 * 1. 在 Vercel 项目中创建 api/reverse.js 文件
 * 2. 或者使用 Vercel CLI: vercel deploy
 * 3. 获取部署后的 URL（例如：https://your-project.vercel.app/api/reverse）
 * 4. 在后端配置中使用此 URL
 */

export default async function handler(req, res) {
  // 只允许 GET 请求
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // 获取查询参数
  const { lat, lon, format = 'json', addressdetails = '1' } = req.query;

  // 验证必需参数
  if (!lat || !lon) {
    return res.status(400).json({ 
      error: 'Missing required parameters',
      message: 'lat and lon are required'
    });
  }

  // 构建 Nominatim API URL
  const nominatimUrl = new URL('https://nominatim.openstreetmap.org/reverse');
  nominatimUrl.searchParams.append('lat', lat);
  nominatimUrl.searchParams.append('lon', lon);
  nominatimUrl.searchParams.append('format', format);
  nominatimUrl.searchParams.append('addressdetails', addressdetails);
  nominatimUrl.searchParams.append('accept-language', 'zh-CN,en');

  // 添加其他查询参数（如果有）
  Object.keys(req.query).forEach(key => {
    if (!['lat', 'lon', 'format', 'addressdetails'].includes(key)) {
      nominatimUrl.searchParams.append(key, req.query[key]);
    }
  });

  try {
    // 设置超时时间（Vercel 免费版限制是 10 秒）
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000); // 8秒超时

    // 转发请求到 Nominatim API
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
      return res.status(response.status).json({
        error: 'Nominatim API error',
        status: response.status,
        statusText: response.statusText
      });
    }

    // 获取响应数据
    const data = await response.json();

    // 返回响应（添加 CORS 头）
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.setHeader('Content-Type', 'application/json');

    return res.status(200).json(data);

  } catch (error) {
    // 处理错误
    console.error('Nominatim API proxy error:', error);

    let statusCode = 500;
    let errorMessage = error.message;

    if (error.name === 'AbortError' || error.message.includes('timeout') || error.message.includes('aborted')) {
      statusCode = 504; // Gateway Timeout
      errorMessage = 'Nominatim API request timeout (Vercel timeout limit: 8s, free tier limit: 10s)';
    } else if (error.message.includes('fetch failed') || error.message.includes('network')) {
      statusCode = 502; // Bad Gateway
      errorMessage = 'Failed to connect to Nominatim API';
    }

    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'application/json');

    return res.status(statusCode).json({
      error: 'Proxy error',
      message: errorMessage,
      type: error.name,
      timestamp: new Date().toISOString()
    });
  }
}

