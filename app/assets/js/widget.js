(function () {
    const style = document.createElement('style');
    style.textContent = `
      .my-widget-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #005fff;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 12px 20px;
        cursor: pointer;
        z-index: 9999;
        font-family: sans-serif;
      }
    `;
  
    const button = document.createElement('button');
    button.className = 'my-widget-button';
    button.innerText = 'ðŸ’¬ Chat with us !';
  
    button.onclick = function () {
      const iframe = document.createElement('iframe');
      iframe.src = '{{ conversation_url }}'; // Injected dynamically
      iframe.allow = 'camera; microphone; fullscreen; display-capture';
 // or Tavus video link
      iframe.style = `
        position: fixed;
        bottom: 70px;
        right: 20px;
        width: 400px;
        height: 600px;
        border: none;
        z-index: 10000;
        box-shadow: 0 0 10px rgba(0,0,0,0.3);
      `;
      document.body.appendChild(iframe);
    };
  
    document.head.appendChild(style);
    document.body.appendChild(button);
  })();
  