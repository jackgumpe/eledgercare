// Loopback-only same-origin static Angular bundle and stream-preserving API proxy.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve('web/dist/eledgercare-web/browser');
http.createServer((req,res)=>{
  if(req.url.startsWith('/api/')){
    const upstream=http.request({hostname:'127.0.0.1',port:5814,path:req.url,method:req.method,
      headers:{...req.headers,host:'127.0.0.1:5814'}}, r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res);});
    upstream.on('error',()=>{res.writeHead(502);res.end();});
    return req.pipe(upstream);
  }
  const leaf=new URL(req.url,'http://127.0.0.1/').pathname.slice(1);
  let file=path.resolve(root,leaf);
  if(!file.startsWith(root+path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile())
    file=path.join(root,'index.html');
  const type={'.js':'application/javascript','.css':'text/css','.html':'text/html'}[path.extname(file)];
  res.writeHead(200,{'Content-Type':type??'application/octet-stream'});
  fs.createReadStream(file).pipe(res);
}).listen(4814,'127.0.0.1');
