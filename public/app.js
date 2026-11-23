const fileInput=document.querySelector("#videoFile");
const preview=document.querySelector("#preview");
const fileInfo=document.querySelector("#fileInfo");
const scriptBox=document.querySelector("#script");
const statusBox=document.querySelector("#status");
const processBtn=document.querySelector("#processBtn");
let selectedFile=null;
let previewUrl=null;

document.querySelectorAll('input[name="mode"]').forEach(input=>input.addEventListener("change",()=>{
  document.querySelectorAll(".choice").forEach(card=>card.classList.toggle("selected",card.querySelector("input").checked));
  scriptBox.hidden=document.querySelector('input[name="mode"]:checked').value!=="script";
}));

fileInput.addEventListener("change",()=>{
  selectedFile=fileInput.files?.[0]||null;
  if(previewUrl)URL.revokeObjectURL(previewUrl);
  preview.hidden=!selectedFile;
  if(!selectedFile){fileInfo.textContent="*El límite debe validarse también en el servidor.";return;}
  if(!selectedFile.type.startsWith("video/")){selectedFile=null;fileInfo.textContent="El archivo seleccionado no parece ser un vídeo.";return;}
  previewUrl=URL.createObjectURL(selectedFile);
  preview.src=previewUrl;
  fileInfo.textContent=selectedFile.name+" · "+(selectedFile.size/1024/1024).toFixed(1)+" MB";
});

processBtn.addEventListener("click",async()=>{
  if(!selectedFile){statusBox.textContent="Primero selecciona un vídeo.";return;}
  const mode=document.querySelector('input[name="mode"]:checked').value;
  const script=scriptBox.value.trim();
  if(mode==="script"&&!script){statusBox.textContent="Añade el guion para continuar.";return;}
  statusBox.textContent="Enviando vídeo al servidor…";
  processBtn.disabled=true;
  try{
    const data=new FormData();
    data.append("file",selectedFile);
    data.append("mode",mode);
    data.append("script",script);
    data.append("language",document.querySelector("#language").value);
    data.append("voice",document.querySelector("#voice").value);
    data.append("resolution",document.querySelector("#resolution").value);
    data.append("keep_audio",document.querySelector("#keepAudio").checked?"true":"false");
    data.append("translate_audio",document.querySelector("#translateAudio").checked?"true":"false");
    data.append("target_language","es");
    data.append("translate_screen_text",document.querySelector("#translateScreenText").checked?"true":"false");
    const response=await fetch("/api/jobs",{method:"POST",body:data});
    if(!response.ok)throw new Error("El servidor no está disponible o rechazó el archivo.");
    const job=await response.json();
    statusBox.textContent="Trabajo recibido: "+job.id+". La integración de doblaje IA y renderizado aún está pendiente.";
  }catch(error){
    statusBox.textContent="Prototipo preparado. Para procesar vídeos, configura el backend y conecta los proveedores de IA.";
  }finally{processBtn.disabled=false;}
});

if("serviceWorker" in navigator)window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));