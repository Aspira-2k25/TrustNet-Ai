const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const root=__dirname,manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8'));
if(manifest.manifest_version!==3||JSON.stringify(manifest.permissions)!=='["storage"]')throw Error('Unexpected extension permissions');
if(manifest.host_permissions.some(origin=>!['http://localhost:8000/*','http://127.0.0.1:8000/*'].includes(origin)))throw Error('Unexpected network permission');
if(manifest.content_scripts.some(script=>JSON.stringify(script.matches)!=='["https://mail.google.com/*"]'))throw Error('Unexpected mailbox permission');
const sourceCatalog=fs.readFileSync(path.join(root,'../../shared/presentation/translations.json'),'utf8');
fs.writeFileSync(path.join(root,'translations.js'),"// Generated from shared/presentation/translations.json. Run npm run build after editing the source.\nvar TrustNetWords = "+sourceCatalog.trim()+";\nif(typeof module!=='undefined')module.exports=TrustNetWords;\n");
fs.copyFileSync(path.join(root,'../../shared/presentation/tokens.css'),path.join(root,'tokens.css'));
const files=['tokens.css','translations.js','manifest.json' ,'worker.js','extract.js','presentation.js','content.js','panel.css','options.html','options.js','options.css','fonts/IBMPlexSans.ttf','fonts/OFL.txt','README.md'];
for(const name of files.filter(name=>name.endsWith('.js')))execFileSync(process.execPath,['--check',path.join(root,name)],{stdio:'pipe'});
if(/innerHTML|insertAdjacentHTML/.test(fs.readFileSync(path.join(root,'content.js'),'utf8')))throw Error('Untrusted HTML interpolation is prohibited');
const output=path.join(root,'dist','trustnet-mail');fs.mkdirSync(output,{recursive:true});const sums={};
for(const name of files){const source=path.join(root,name),target=path.join(output,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(source,target);sums[name]=crypto.createHash('sha256').update(fs.readFileSync(target)).digest('hex');}
fs.writeFileSync(path.join(output,'checksums.json'),JSON.stringify(sums,null,2));
console.log(`BUILD PASS: TrustNet Mail ${manifest.version}; ${files.length} runtime files; no bundler, remote code or paid APIs. Load unpacked: ${output}`);
