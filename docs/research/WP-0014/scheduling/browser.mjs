// Drives the accepted Angular bundle in real independent Edge contexts. Only the event observer is injected.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
const require = createRequire(path.resolve('web/package.json'));
const {chromium} = require('playwright');
const root = process.argv[2];
const cfg = JSON.parse(fs.readFileSync(path.join(root, 'config.json')));
const control = path.join(root, 'control');
const base = 'http://127.0.0.1:4814';
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
function event(name, data = {}) {
  fs.appendFileSync(path.join(root, 'browser.jsonl'), JSON.stringify({name, t_ms:Date.now(),...data}) + '\n');
}
async function waitForFile(f) {
  const start = Date.now();
  while (!fs.existsSync(path.join(control, f))) {
    if (Date.now() - start > 350000 || fs.existsSync(path.join(control, 'engine.dead'))) throw Error('ready failure');
    await wait(25);
  }
}
const browser = await chromium.launch({channel:'msedge',headless:true,args:['--disable-gpu']});
try {
  event('browser', {version:browser.version()});
  const clients = await Promise.all(cfg.inputs.map(async key => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.exposeBinding('diag', (_, name, browser_ms, details) => {
      event(name,{key,browser_ms,...details});
    });
    await page.addInitScript(() => {
      const now=()=>performance.timeOrigin+performance.now();
      document.addEventListener('change', e => {
        if(e.target.matches('[data-testid="file-input"]')) window.diag('select',now(),{});
      },true);
      document.addEventListener('click',e=>{
        const id=e.target.closest('[data-testid]')?.getAttribute('data-testid');
        if (id === 'request-extraction' || id === 'submit') window.diag(id,now(),{});
      },true);
      let captured=false;
      const observer=new MutationObserver(()=>{
        if(captured) return;
        const article=document.querySelector('[data-testid="result-page-1"]');
        if (!article?.getBoundingClientRect().height || !article.innerText.trim()) return;
        captured=true;
        const box=article.getBoundingClientRect();
        window.diag('result_layout',now(),{inViewport:box.top<innerHeight && box.bottom>0});
        article.scrollIntoView();
        requestAnimationFrame(()=>requestAnimationFrame(()=>{
          const box=article.getBoundingClientRect();
          window.diag('result_viewport_frame',now(),{inViewport:box.top<innerHeight && box.bottom>0});
        }));
      });
      observer.observe(document,{childList:true,subtree:true});
    });
    page.on('response', resp => {
      if(resp.url().endsWith('/extraction')) event('http_response',{key,method:resp.request().method(),code:resp.status()});
    });
    await page.goto(base);
    await page.getByTestId('file-input').waitFor();
    event('intake_open',{key,browser_ms:await page.evaluate(()=>performance.timeOrigin+performance.now())});
    if (['immediate','ready'].includes(cfg.mode))
      fs.writeFileSync(path.join(control,'prepare.'+key),'intake visible');
    return {page,key};
  }));
  // Select both before waiting for either upload to complete; both early signals reach the same manager.
  await Promise.all(clients.map(async ({page,key})=>{
    await page.getByTestId('file-input').setInputFiles(cfg.files[key]);
    await page.getByTestId('submit').click();
    await page.getByTestId('receipt-open').click();
    await page.getByTestId('request-extraction').waitFor();
    event('upload_opened',{key,doc:page.url().split('/').pop()});
  }));
  if(cfg.mode==='ready') await waitForFile('ready');
  const drive=async ({page,key},i)=>{
    // Fixed offset makes ordering explicit without waiting for client A to complete.
    if (i) await wait(180);
    const doc=page.url().split('/').pop();
    await page.getByTestId('request-extraction').click();
    if(cfg.cpu_crash) {
      await page.getByTestId('extraction-failure').waitFor({timeout:50000});
      const view=await (await page.request.get(base+'/api/documents/'+doc+'/extraction')).json();
      if (view.result || view.status!=='failed') throw Error('crash incorrectly published');
      event('failure_verified',{key,doc,status:view.status,detail:view.currentAttempt});
      return;
    }
    await Promise.race([page.getByTestId('result-page-1').waitFor({timeout:350000}),
      page.getByTestId('extraction-failure').waitFor({timeout:350000}).then(async()=>{
        throw Error(await page.getByTestId('extraction-failure').innerText());})]);
    await page.waitForFunction(()=>document.querySelector('[data-testid="result-page-1"]')?.innerText.length>0);
    const saved=await (await page.request.get(base+'/api/documents/'+doc+'/extraction')).json();
    const r=saved.result;
    const original = await (await page.request.get(base+'/api/documents/'+doc+'/original')).body();
    if (hash(original)!==cfg.hashes[key] || hash(Buffer.from(r.rawText))!==r.rawSha256 ||
        r.rawSha256!==(await page.getByTestId('result-raw-sha256').innerText()).trim() ||
        r.rawText!==(await page.getByTestId('result-raw-text').textContent()) ||
        r.attemptId!==saved.currentAttempt.attemptId || r.pageCount!==1) throw Error('result identity');
    fs.writeFileSync(path.join(root,'saved-'+key+'.json'),JSON.stringify(saved,null,2));
    await page.getByTestId('open-work-order-review').click();
    for (const [index,label] of ['first','second'].entries()) {
      await page.getByTestId('input-operator-label').fill('Diagnostic '+label);
      await page.getByTestId('save-draft').click();
      await page.getByTestId('history-row-'+(index+1)).waitFor();
    }
    await page.reload();
    await page.getByTestId('view-revision-1').click();
    await page.getByTestId('historical-revision-banner').waitFor();
    const originalLink=await page.getByTestId('pdf-open-fallback').getAttribute('href');
    const bytes=await (await page.request.get(new URL(originalLink,base).href)).body();
    if(hash(bytes)!==cfg.hashes[key] || await page.getByTestId('review-result-id').textContent()!==r.resultId)
      throw Error('reopen provenance');
    event('reopened',{key,doc,attempt:r.attemptId,raw:r.rawSha256,original:hash(bytes),
      historical:(await page.getByTestId('historical-revision-banner').innerText()).trim()});
  };
  await Promise.all(clients.map(drive));
} finally {
  await browser.close();
}
