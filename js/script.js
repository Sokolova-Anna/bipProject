const ButtonAuth = document.querySelectorAll('.description__auth');
const authForm = document.querySelector('.alert') 
ButtonAuth.forEach(item => { item.addEventListener("click", (e) => {
    e.preventDefault(); 
    authForm.classList.remove("hide");
}); });
