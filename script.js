const year = document.getElementById("year");
year.textContent = new Date().getFullYear();

const typingText = document.getElementById("typingText");
const text = "Refining the checkout experience...";
let index = 0;

function typeText() {
  if (index <= text.length) {
    typingText.textContent = text.slice(0, index);
    index += 1;
    setTimeout(typeText, 55);
  } else {
    setTimeout(() => {
      index = 0;
      typeText();
    }, 1800);
  }
}
typeText();

const downloadButton = document.getElementById("downloadButton");
const toast = document.getElementById("toast");
downloadButton.addEventListener("click", () => {
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3800);
});
