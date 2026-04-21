import "htmx.org";

import hljs from "highlight.js";
window.hljs = hljs;
import "highlight.js/styles/github-dark.css";
import("highlightjs-line-numbers.js").then(() => {
  console.log(window.hljs.initLineNumbersOnLoad());
  document.querySelectorAll(".code").forEach((block) => {
    hljs.highlightElement(block);
    hljs.lineNumbersBlock(block);
  });
});

document.body.addEventListener("htmx:responseError", (e) => {
  alert(e.detail.xhr.responseText);
});

document
  .querySelectorAll("form")
  .forEach((f) =>
    f.addEventListener("submit", () =>
      f.querySelectorAll(".err").forEach((e) => e.remove()),
    ),
  );

const diff = document.querySelectorAll(".diff").forEach((diff) => {
  console.log(diff);
  diff2htmlUi = new Diff2HtmlUI(diff, diff.dataset.diff, {
    drawFileList: true,
    matching: "lines",
  });
  diff2htmlUi.draw();
});
