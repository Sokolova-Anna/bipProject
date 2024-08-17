const buttonAuthElement  = document.querySelector('.description__auth');
const authForm = document.querySelector('.alert') 
if (buttonAuthElement ) {
    buttonAuthElement .addEventListener("click", (e) => {
    e.preventDefault(); 
    authForm.classList.remove("hide");
}); 
}


const ButtonCloseAuth = document.querySelector('.alert__close');
if (ButtonCloseAuth) {
    ButtonCloseAuth.addEventListener("click", (e) => {
        e.preventDefault(); 
        authForm.classList.add("hide");   
    })
}

const ButtonHeaderMap = document.querySelector('.header__map');
if (ButtonHeaderMap) {
    ButtonHeaderMap.addEventListener("click", () => {
        location='map.html'
    })
}

const ButtonHeaderMain = document.querySelector('.header__main');
if (ButtonHeaderMain) {
    ButtonHeaderMain.addEventListener("click", () => {
        location='index.html'
    })
}


