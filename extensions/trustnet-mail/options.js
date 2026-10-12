const status=document.getElementById('status');
document.getElementById('connect').onsubmit=async event=>{
 event.preventDefault();status.textContent='Connecting…';
 const password=document.getElementById('password');
 try {const result=await chrome.runtime.sendMessage({action:'CONNECT',origin:document.getElementById('origin').value,email:document.getElementById('email').value,password:password.value});status.textContent=result.ok?'Connected. Open Gmail and click TrustNet Scan.':result.error;}catch{status.textContent='Connection unavailable. Start TrustNet and retry.';}finally{password.value='';}
};
document.getElementById('disconnect').onclick=async()=>{await chrome.runtime.sendMessage({action:'DISCONNECT'});status.textContent='Disconnected; session token cleared.';};
