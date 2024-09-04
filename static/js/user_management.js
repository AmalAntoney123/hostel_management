document.addEventListener('DOMContentLoaded', function() {
    const addStudentForm = document.getElementById('add-student-form');
    const addStaffForm = document.getElementById('add-staff-form');
    const studentListBody = document.getElementById('student-list-body');
    const staffListBody = document.getElementById('staff-list-body');

    function handleFormSubmit(event, role) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.role = role;

        fetch('/add_user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert(`${role} added successfully. Username: ${result.username}, Password: ${result.password}, Email: ${result.email}`);
                form.reset();
                fetchUserList(role);
            } else {
                alert(`Error: ${result.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while adding the user.');
        });
    }

    function fetchUserList(role) {
        fetch(`/get_users/${role}`)
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    const listBody = role === 'student' ? studentListBody : staffListBody;
                    listBody.innerHTML = '';
                    result.users.forEach(user => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${user.username}</td>
                            <td>${user.full_name}</td>
                            <td>${user.email}</td>
                            <td>${user.phone}</td>
                        `;
                        listBody.appendChild(row);
                    });
                } else {
                    console.error(`Error fetching ${role} list:`, result.message);
                }
            })
            .catch(error => {
                console.error(`Error fetching ${role} list:`, error);
            });
    }

    if (addStudentForm) {
        addStudentForm.addEventListener('submit', (event) => handleFormSubmit(event, 'student'));
        fetchUserList('student');
    }

    if (addStaffForm) {
        addStaffForm.addEventListener('submit', (event) => handleFormSubmit(event, 'staff'));
        fetchUserList('staff');
    }
});