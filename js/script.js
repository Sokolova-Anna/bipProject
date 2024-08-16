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

ymaps.ready(function () {
    let myMap = new ymaps.Map("YMapsID", {
      center: [59.93, 30.31], //saint-p
      zoom: 10
    });

    let myPlacemark1 = new ymaps.Placemark([59.963966, 30.302487], {
        balloonContent: 'Color Cafe'
    }, {
        iconLayout: 'default#image', // Указываем, что используем свое изображение
        iconImageHref: './images/dog-friendly.png', // Ссылка на ваше изображение
        iconImageSize: [26, 26], // Размеры изображения (ширина, высота)
        iconImageOffset: [-15, -42] // Смещение изображения (по оси X и Y), чтобы центрировать его относительно точки
    });
    

    let myPlacemark2 = new ymaps.Placemark([59.946200, 30.373191], {
        balloonContent: 'Таврический сад'
    }, {
        iconLayout: 'default#image', // Указываем, что используем свое изображение
        iconImageHref: './images/park_mark.png', // Ссылка на ваше изображение
        iconImageSize: [26, 26], // Размеры изображения (ширина, высота)
        iconImageOffset: [-15, -42] // Смещение изображения (по оси X и Y), чтобы центрировать его относительно точки
    });


    myMap.geoObjects.add(myPlacemark1);
    myMap.geoObjects.add(myPlacemark2);
  });