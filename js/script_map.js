
//--кнопка регистрации на главном экране
const ButtonAuth = document.querySelectorAll('.description__auth');
const authForm = document.querySelector('.alert') 
ButtonAuth.forEach(item => { item.addEventListener("click", (e) => {
    e.preventDefault(); 
    authForm.classList.remove("hide");
}); });


const ButtonCloseAuth = document.querySelector('.alert__close');
ButtonCloseAuth.addEventListener("click", (e) => {
    e.preventDefault(); 
    authForm.classList.add("hide");   
})

const ButtonHeaderMap = document.querySelector('.header__map');
ButtonHeaderMap.addEventListener("click", () => {
    location='map.html'
})

const ButtonHeaderMain = document.querySelector('.header__main');
ButtonHeaderMain.addEventListener("click", () => {
    location='index.html'
})



