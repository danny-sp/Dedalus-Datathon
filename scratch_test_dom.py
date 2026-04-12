import streamlit as st
import streamlit.components.v1 as components

st.chat_input("Escribe algo...")

js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    var parentDoc = window.parent.document;
    console.log(parentDoc);
    var chatInputBtn = parentDoc.querySelector('[data-testid="stChatInputSubmitButton"]');
    if (chatInputBtn) {
        var btn = parentDoc.createElement("button");
        btn.innerHTML = "🎤";
        btn.style.marginRight = "10px";
        chatInputBtn.parentNode.insertBefore(btn, chatInputBtn);
    }
});
</script>
"""
components.html(js, height=0, width=0)
