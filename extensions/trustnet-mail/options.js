/* Settings send credentials only on form submission. Passwords are never saved. */
(() => {
 const $=id=>document.getElementById(id),P=globalThis.TrustNetPresentation;
 let language='en',busy=false;
 const t=(en,hi)=>P.text(language,en,hi),rpc=request=>chrome.runtime.sendMessage(request);
 function copy(){
  $('heading').textContent=t('Connect TrustNet','TrustNet connect karein');
  $('intro').textContent=t('Start TrustNet, then sign in with your website account. Your password is not saved. Reconnect after a browser restart.','TrustNet start karein, phir website account se sign in karein. Password save nahi hota. Browser restart ke baad dobara connect karein.');
  $('help').textContent=t('Open an email in Gmail and click Scan message. Only that opened message is checked. Websites are contacted only when you click Check this website.','Gmail mein email kholein aur Message check karein dabayein. Sirf wahi khula message check hoga. Website sirf Website check karein dabane par khulegi.');
  $('notice').textContent=P.notice(language);$('connect-button').textContent=t('Connect','Connect karein');$('disconnect').textContent=t('Disconnect','Disconnect karein');$('origin-label').textContent=t('Local server','Local server');$('email-label').textContent=t('Email','Email');$('password-label').textContent=t('Password','Password');$('website').textContent=t('Open TrustNet / create an account','TrustNet kholein / account banayein');$('language').value=language;
 }
 async function status(){
  try{const r=await rpc({action:'STATUS'});$('status').textContent=!r.ok?t('Connection unavailable. Start TrustNet and retry.','Connection nahi mila. TrustNet start karke dobara karein.'):r.connected?t('Connected. Ready to check an opened email.','Connected. Khula email check kar sakte hain.'):r.backend?t('Sign in to connect. Your session may have expired.','Connect karne ke liye sign in karein. Session expire hua ho sakta hai.'):t('Local server is offline. Start TrustNet.','Local server band hai. TrustNet start karein.');}catch{$('status').textContent=t('Extension unavailable. Reload it and try again.','Extension nahi chal rahi. Reload karke dobara karein.');}
 }
 $('connect').onsubmit=async event=>{
  event.preventDefault();if(busy)return;busy=true;$('connect-button').disabled=true;$('status').textContent=t('Connecting...','Connect ho raha hai...');
  try{const response=await rpc({action:'CONNECT',origin:$('origin').value,email:$('email').value.trim(),password:$('password').value});if(!response.ok)throw new Error(response.error);await status();}catch{$('status').textContent=t('Could not sign in. Check your account, password and local server.','Sign in nahi hua. Account, password aur local server check karein.');}finally{$('password').value='';busy=false;$('connect-button').disabled=false;}
 };
 $('disconnect').onclick=async()=>{try{await rpc({action:'DISCONNECT'});$('status').textContent=t('Disconnected. Saved login removed.','Disconnected. Saved login hata diya.');}catch{$('status').textContent=t('Could not disconnect. Reload the extension.','Disconnect nahi hua. Extension reload karein.');}};
 $('language').onchange=async()=>{language=$('language').value==='hi'?'hi':'en';try{await rpc({action:'SET_LANGUAGE',language});}catch{}copy();await status();};
 rpc({action:'GET_LANGUAGE'}).then(r=>{language=r.language==='hi'?'hi':'en';copy();return status();}).catch(()=>{copy();status();});copy();
})();
