// ===============================
// MENÚ RESPONSIVE
// ===============================

const menuBtn = document.getElementById("menu-btn");
const navLinks = document.getElementById("nav-links");

menuBtn.addEventListener("click", () => {
    navLinks.classList.toggle("mostrar");
});


// ===============================
// CERRAR MENÚ AL HACER CLIC
// ===============================

const enlaces = document.querySelectorAll(".nav-links a");

enlaces.forEach(enlace => {
    enlace.addEventListener("click", () => {
        navLinks.classList.remove("mostrar");
    });
});


// ===============================
// ENLACE ACTIVO SEGÚN SECCIÓN
// ===============================

const secciones = document.querySelectorAll("section[id]");
const enlacesMenu = document.querySelectorAll(".nav-links a");

window.addEventListener("scroll", () => {

    let posicionActual = window.scrollY;

    secciones.forEach(seccion => {

        const inicio = seccion.offsetTop - 150;
        const altura = seccion.offsetHeight;
        const id = seccion.getAttribute("id");

        if (
            posicionActual >= inicio &&
            posicionActual < inicio + altura
        ) {

            enlacesMenu.forEach(enlace => {
                enlace.classList.remove("activo");
            });

            const enlaceActivo = document.querySelector(
                `.nav-links a[href="#${id}"]`
            );

            if (enlaceActivo) {
                enlaceActivo.classList.add("activo");
            }
        }

    });

});