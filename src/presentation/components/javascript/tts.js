setInterval(function() {
    const parentDoc = window.parent.document;
    const ttsData = __TTS_DATA__;
    
    const speakerSvg = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="20" height="20">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" fill="currentColor"/>
        </svg>
    `;
    const stopSvg = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="20" height="20">
            <path d="M6 6h12v12H6z" fill="currentColor"/>
        </svg>
    `;
    
    for (const [i, text] of Object.entries(ttsData)) {
        const anchor = parentDoc.getElementById('tts-anchor-' + i);
        if (anchor) {
            let btn = anchor.querySelector('.tts-custom-btn');
            if (btn) {
                if (btn._myIframe === window) {
                    continue; // Button is alive and owned by this iframe
                }
                btn.remove(); // Button belongs to dead iframe, trash it
            }
            
            btn = parentDoc.createElement('button');
            btn.className = "tts-custom-btn";
            btn._myIframe = window;
            btn.innerHTML = speakerSvg;
            btn.title = "Escuchar respuesta";
            btn.dataset.playing = "false";
            btn.style.cssText = `
                background: transparent;
                border: 1px solid rgba(125,125,125,0.2);
                border-radius: 5px;
                color: #888;
                cursor: pointer;
                padding: 6px 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s;
            `;
            
            btn.onmouseover = () => btn.style.background = 'rgba(125,125,125,0.1)';
            btn.onmouseout = () => btn.style.background = 'transparent';
            
            btn.onclick = () => {
                const synth = window.parent.speechSynthesis;
                
                if (btn.dataset.playing === "true") {
                    // Stop playing
                    synth.cancel();
                    btn.dataset.playing = "false";
                    btn.innerHTML = speakerSvg;
                    btn.style.color = "#888";
                    return;
                }
                
                // Cancel any audio currently playing
                synth.cancel();
                
                // Reset all other TTS buttons
                const allBtns = parentDoc.querySelectorAll('.tts-custom-btn');
                allBtns.forEach(b => {
                    b.dataset.playing = "false";
                    b.innerHTML = speakerSvg;
                    b.style.color = "#888";
                });
                
                const msg = new window.parent.SpeechSynthesisUtterance(text);
                msg.lang = 'es-ES';
                
                // Keep global reference to avoid Safari/Chrome garbage collection bug ending speech early
                window.parent._currentTTSUtterance = msg;
                
                msg.onend = () => {
                    btn.dataset.playing = "false";
                    btn.innerHTML = speakerSvg;
                    btn.style.color = "#888";
                };
                msg.onerror = () => {
                    btn.dataset.playing = "false";
                    btn.innerHTML = speakerSvg;
                    btn.style.color = "#888";
                };
                
                btn.dataset.playing = "true";
                btn.innerHTML = stopSvg;
                btn.style.color = "#ff4b4b"; // Red to indicate playing/stop
                
                synth.speak(msg);
            };
            
            anchor.appendChild(btn);
        }
    }
}, 1000);
