// static/register.js

document.getElementById('registerForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const roleSelect = document.getElementById('role');
    const messageDiv = document.getElementById('message');

    const username = usernameInput.value;
    const password = passwordInput.value;
    const role = roleSelect.value;

    messageDiv.textContent = ''; // Clear previous messages

    try {
        const response = await fetch('http://127.0.0.1:8000/users/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            },
            body: JSON.stringify({ username, password, role })
        });

        const data = await response.json();

        if (response.ok) {
            messageDiv.className = 'success';
            messageDiv.textContent = 'Registration successful! You can now login.';
            // Clear the form
            usernameInput.value = '';
            passwordInput.value = '';
            // Optionally redirect to login page after a delay
            // setTimeout(() => { window.location.href = '/static/index.html'; }, 2000);
        } else {
            messageDiv.className = 'error';
            messageDiv.textContent = `Registration Failed: ${data.detail || response.statusText}`;
        }

    } catch (error) {
        messageDiv.className = 'error';
        messageDiv.textContent = `Error: ${error.message}`;
    }
});
