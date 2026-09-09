import json, pathlib, subprocess, sys, tempfile, html, re
source = pathlib.Path(sys.argv[1]).read_text()
results = []
for repeat in range(3):
    with tempfile.TemporaryDirectory(prefix='micro-bench-') as tmp:
        path = pathlib.Path(tmp, 'index.html')
        path.write_text('''<!doctype html><canvas id="micro-scene" style="width:1440px;height:820px"></canvas><button id="pause-motion"></button><button id="reset-view"></button><pre id="result"></pre><script>
window.requestAnimationFrame=()=>1; window.cancelAnimationFrame=()=>{};
window.ResizeObserver=class {observe(){}};
window.IntersectionObserver=class {observe(){}};
</script><script>''' + source + '''
autoMotion=false;resize();
const samples=[];
for(let sample=0;sample<110;sample++) {
 yaw=-.28+Math.sin(sample*.047)*.9; pitch=.4+Math.cos(sample*.053)*.45;
 const start=performance.now();
 draw();context.getImageData(0,0,1,1);
 if(sample>=20) samples.push(performance.now()-start);
}
samples.sort((a,b)=>a-b);
document.querySelector('#result').textContent=JSON.stringify({median:samples[45],p95:samples[85],min:samples[0],max:samples[89],points:points.length,dpr:devicePixelRatio,samples:samples.length});
</script>''')
        run = subprocess.run(['chromium','--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--disable-dev-shm-usage','--force-device-scale-factor=2','--user-data-dir='+tmp+'/profile','--dump-dom',path.as_uri()],capture_output=True,text=True,timeout=90)
        match = re.search(r'<pre id="result">(.*?)</pre>',run.stdout,re.S)
        if not match or not match[1]:
            print(run.stderr[-3000:],run.stdout[-1500:]);sys.exit(1)
        result=json.loads(html.unescape(match[1]));results.append(result)
        print(json.dumps(result),flush=True)
pathlib.Path(sys.argv[2]).write_text(json.dumps(results,indent=2)+'\n')
