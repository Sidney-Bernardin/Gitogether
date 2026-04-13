import "htmx.org";

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
