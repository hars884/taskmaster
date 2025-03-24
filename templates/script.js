document.addEventListener("DOMContentLoaded", function() {
    const loginWrapper = document.querySelector(".login-wrapper");
    const signupWrapper = document.querySelector(".signup-wrapper");
    const loginSwitcher = document.querySelector(".switcher-signup");  // Corrected selector
    const signupSwitcher = document.querySelector(".switcher-login");  // Corrected selector

    signupSwitcher.addEventListener("click", function() {
        loginWrapper.classList.remove("is-active");
        signupWrapper.classList.add("is-active");
    });

    loginSwitcher.addEventListener("click", function() {
        signupWrapper.classList.remove("is-active");
        loginWrapper.classList.add("is-active");
    });
});
