let listMarks = []
const placeForm = document.querySelector('.place');
const BlackBackground = document.querySelector('.image');
const ButtonPlaceClose = document.querySelector('.place__close');

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

    let myPlacemark3 = new ymaps.Placemark([59.991900, 30.216425], {
        balloonContent: 'Яхтенный сквер'
    }, {
        iconLayout: 'default#image', // Указываем, что используем свое изображение
        iconImageHref: './images/mark_commands.png', // Ссылка на ваше изображение
        iconImageSize: [26, 26], // Размеры изображения (ширина, высота)
        iconImageOffset: [-15, -42] // Смещение изображения (по оси X и Y), чтобы центрировать его относительно точки
    });


    myMap.geoObjects.add(myPlacemark1);
    myMap.geoObjects.add(myPlacemark2);
    myMap.geoObjects.add(myPlacemark3);

    listMarks.push(myPlacemark1);
    listMarks.push(myPlacemark2);
    listMarks.push(myPlacemark3);


    listMarks.forEach(item => { item.events.add("click", (e) => {
        e.preventDefault();
        let coords = e.get('coords');   
        if (item.geometry._coordinates[0] == '59.946200' && item.geometry._coordinates[1] == '30.373191') 
            placeForm.classList.remove('hide');
            BlackBackground.classList.remove('hide');
    }); });

  });


if (ButtonPlaceClose) {
    ButtonPlaceClose.addEventListener("click", (e) => {
        e.preventDefault(); 
        placeForm.classList.add("hide");   
        BlackBackground.classList.add('hide');
    })
}

