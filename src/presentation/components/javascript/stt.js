setInterval(function() {
    const parentDoc = window.parent.document;
    if (parentDoc.getElementById('custom-mic-btn')) return; // already exists
    
    // Find the chat input container
    const chatInputContainer = parentDoc.querySelector('[data-testid="stChatInput"]');
    if (!chatInputContainer) return;
    
    // Find the submit button inside it
    const buttons = chatInputContainer.querySelectorAll('button');
    const submitBtn = buttons[buttons.length - 1]; // usually the last button is send
    if (!submitBtn) return;
    
    const micBtn = parentDoc.createElement("button");
    micBtn.id = 'custom-mic-btn';
    micBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="24" height="24">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" fill="currentColor"/>
            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" fill="currentColor"/>
        </svg>
    `;
    micBtn.style.cssText = `
        background: transparent;
        border: none;
        color: #888;
        cursor: pointer;
        padding: 5px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: color 0.3s;
        margin-right: 8px;
    `;
    
    // Stop square SVG for recording state
    const stopSvg = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="24" height="24">
            <path d="M6 6h12v12H6z" fill="currentColor"/>
        </svg>
    `;
    const micSvg = micBtn.innerHTML;

    // Insert before the submit button
    submitBtn.parentNode.insertBefore(micBtn, submitBtn);

    const SpeechRecognition = window.parent.SpeechRecognition || window.parent.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    
    const recognition = new SpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.continuous = false;
    recognition.interimResults = false;

    let isRecording = false;

    micBtn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    };

    recognition.onstart = () => {
        isRecording = true;
        micBtn.innerHTML = stopSvg;
        micBtn.style.color = "red";
    };

    recognition.onresult = (evt) => {
        const transcript = evt.results[0][0].transcript;
        const textArea = chatInputContainer.querySelector('textarea');
        if (textArea) {
            // Set value and trigger React input event
            const nativeSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype, 'value').set;
            let currentVal = textArea.value;
            let spacer = currentVal ? " " : "";
            nativeSetter.call(textArea, currentVal + spacer + transcript);
            textArea.dispatchEvent(new window.parent.Event('input', { bubbles: true }));
            
            // Auto click send to submit the voice input automatically
            setTimeout(() => {
                 const sendBtn = chatInputContainer.querySelectorAll('button');
                 const actualSend = sendBtn[sendBtn.length - 1]; // re-query the button
                 if(actualSend && !actualSend.disabled) actualSend.click();
            }, 100);
        }
    };

    recognition.onend = () => {
        isRecording = false;
        micBtn.innerHTML = micSvg;
        micBtn.style.color = "#888";
    };
    
    recognition.onerror = () => {
        isRecording = false;
        micBtn.innerHTML = micSvg;
        micBtn.style.color = "#888";
    };
}, 1000);
