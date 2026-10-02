const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'dist');
fs.mkdirSync(out,{recursive:true});
for(const f of ['index.html','styles.css','model.js','house-data.js','app.js','land-data.js','land.js','refresh-status.js','refresh-ui.js','refresh-report.json','catalog.json','auto-sync.js','.nojekyll'])fs.copyFileSync(path.join(root,f),path.join(out,f));
console.log('Built static website in dist/.');
