document.addEventListener('DOMContentLoaded', function() {
    const addStudentForm = document.getElementById('add-student-form');
    const addStaffForm = document.getElementById('add-staff-form');
    const studentListBody = document.getElementById('student-list-body');
    const staffListBody = document.getElementById('staff-list-body');

    let studentTable, staffTable;

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

    function initializeDataTable(role) {
        const tableId = `#${role}Table`;
        if ($(tableId).length) {
            if ($.fn.DataTable.isDataTable(tableId)) {
                $(tableId).DataTable().destroy();
            }
            if (role === 'student') {
                studentTable = $(tableId).DataTable();
            } else {
                staffTable = $(tableId).DataTable();
            }
        }
    }

    function fetchUserList(role) {
        fetch(`/get_users/${role}`)
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    const tableId = `#${role}Table`;
                    const table = $(tableId).DataTable();
                    
                    // Clear existing data
                    table.clear();
                    
                    // Add new data
                    result.users.forEach(user => {
                        table.row.add([
                            user.username,
                            user.full_name,
                            user.email,
                            user.phone,
                            user.is_active ? 'Active' : 'Disabled',
                            `<button class="btn btn-sm btn-${user.is_active ? 'warning' : 'success'} toggle-status" data-username="${user.username}" data-role="${role}">${user.is_active ? 'Disable' : 'Enable'}</button>
                             <button class="btn btn-sm btn-primary reset-password" data-username="${user.username}" data-role="${role}">Reset Password</button>`
                        ]);
                    });
                    
                    // Redraw the table
                    table.draw();
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

    // Move DataTables initialization here
    if ($('#studentTable').length) {
        studentTable = $('#studentTable').DataTable();
    }
    if ($('#staffTable').length) {
        staffTable = $('#staffTable').DataTable();
    }

    $(document).ready(function() {
        // Initialize DataTables
        $('#studentTable').DataTable();
        $('#staffTable').DataTable();

        // Fetch initial data
        fetchUserList('student');
        fetchUserList('staff');

        $('#bulk-upload-form').on('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(this);
            
            $.ajax({
                url: '/bulk_upload_users',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(response) {
                    $('#upload-result').html('<div class="alert alert-success">Upload successful. ' + response.message + '</div>');
                },
                error: function(xhr, status, error) {
                    $('#upload-result').html('<div class="alert alert-danger">Upload failed. ' + xhr.responseJSON.message + '</div>');
                }
            });
        });

        // Event delegation for toggle status and reset password buttons
        $(document).on('click', '.toggle-status', function() {
            const username = $(this).data('username');
            const role = $(this).data('role');
            toggleUserStatus(username, role);
        });

        $(document).on('click', '.reset-password', function() {
            const username = $(this).data('username');
            const role = $(this).data('role');
            resetUserPassword(username, role);
        });
    });

    function toggleUserStatus(username, role) {
        fetch('/toggle_user_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, role }),
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert(`User status updated successfully.`);
                fetchUserList(role);
            } else {
                alert(`Error: ${result.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while updating user status.');
        });
    }

    function resetUserPassword(username, role) {
        fetch('/reset_user_password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, role }),
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert(`Password reset successfully. New password: ${result.password}`);
            } else {
                alert(`Error: ${result.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while resetting the password.');
        });
    }
});