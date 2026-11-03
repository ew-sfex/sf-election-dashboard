(function () {
  if (window.__sfElectionEmbedListenerAttached) return;
  window.__sfElectionEmbedListenerAttached = true;

  window.addEventListener('message', function (event) {
    var data = event.data;
    if (!data || data.type !== 'sf-election-embed-resize') return;
    var height = Number(data.height);
    if (!height || height < 100) return;

    var iframes = document.querySelectorAll('iframe');
    for (var i = 0; i < iframes.length; i++) {
      var iframe = iframes[i];
      if (iframe.contentWindow === event.source) {
        var newHeight = (height + 4) + 'px';
        iframe.style.height = newHeight;
        iframe.setAttribute('height', String(height + 4));
        iframe.style.overflow = 'hidden';
        iframe.setAttribute('scrolling', 'no');
        return;
      }
    }
  });
})();
