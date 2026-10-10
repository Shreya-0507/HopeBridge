const token = localStorage.getItem("access_token");

if (!token) {
    window.location.href = "login.html";
}
function openAwareness() {
    window.location.href = "awareness.html";
}
function openRecovery() {
    window.location.href = "recovery.html";
}

function openProgress() {
    window.location.href = "progress.html";
}
async function markProgress() {

    const token = localStorage.getItem("access_token");

    if (!token) {
        document.getElementById("progressMessage").textContent =
            "Please login again.";
        return;
    }

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/progress",
            {
                method: "POST",

                headers: {
                    "Authorization": "Bearer " + token
                }
            }
        );

        const data = await response.json();

        document.getElementById("progressMessage").textContent =
            data.message;

    } catch (error) {

        document.getElementById("progressMessage").textContent =
            "Unable to connect to backend.";

        console.error(error);
    }
}
function openSupport() {
    window.location.href = "support.html";
}

function logout() {

    localStorage.removeItem("access_token");
    localStorage.removeItem("user_name");

    window.location.href = "login.html";
}
function openSelfAssessment() {
    window.location.href = "assessment.html";
}
async function submitAssessment(event) {

    event.preventDefault();

    const answers = [];

    for (let i = 0; i < 5; i++) {

        const selected = document.querySelector(
            `input[name="question${i}"]:checked`
        );

        if (!selected) {
            alert("Please answer all questions.");
            return;
        }

        answers.push(Number(selected.value));
    }

    const resultBox = document.getElementById("assessmentResult");

    resultBox.innerHTML = `
        <p>Calculating your result...</p>
    `;

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/self-assessment",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(answers)
            }
        );

        const data = await response.json();

        resultBox.innerHTML = `
            <div class="assessment-result">
                 <h2>📊 Your Result</h2>
                 <h3>${data.result}</h3>
                 <p>
                    Score: ${data.score} 
                </p>
                 <p>
                   ${data.message}
                </p>
                <p>
                  <strong>
                      This result is for awareness only and is
                       not a medical diagnosis.
                 </strong>
               </p>

                <button onclick="location.reload()">
                     🏠 Back to Dashboard
               </button>

            </div>
        `;

        resultBox.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {

        resultBox.innerHTML = `
            <p>Unable to connect to backend.</p>
        `;

        console.error(error);
    }
}
function openPledge() {
    window.location.href = "pledge.html";
}
function openHelp() {

    window.location.href = "help.html";

}