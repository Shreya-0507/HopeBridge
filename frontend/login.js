const form = document.getElementById("loginForm");

form.addEventListener("submit", async function(event) {

    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const loginData = {
        email: email,
        password: password
    };

    try {

        const response = await fetch(
            "http://hopebridge-backend-5xfs.onrender.com/login",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(loginData)
            }
        );

        const data = await response.json();

        document.getElementById("message").textContent =
            data.message;

       if (data.message === "Login successful") {

    localStorage.setItem(
        "access_token",
        data.access_token
    );

    localStorage.setItem(
        "user_name",
        data.name
    );

    window.location.href = "dashboard.html";
}

    } catch (error) {

        document.getElementById("message").textContent =
            "Unable to connect to backend.";

        console.error(error);
    }

});