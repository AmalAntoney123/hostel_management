$(document).ready(function () {
    let isSubmitting = false;

    window.handleFormSubmit = function(event, role) {
        event.preventDefault();
        console.log(`Form submission attempt for ${role}`);

        if (isSubmitting) {
            console.log('Submission already in progress, ignoring');
            return false;
        }

        isSubmitting = true;
        console.log('Starting submission process');

        const $form = $(event.target);
        const data = $form.serializeArray().reduce((obj, item) => {
            obj[item.name] = item.value;
            return obj;
        }, {});
        data.role = role;

        console.log('Sending data:', data);

        $.ajax({
            url: '/admin/add_user',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function (result) {
                console.log('Received response:', result);
                if (result.success) {
                    alert(`${role} added successfully. Username: ${result.username}, Password: ${result.password}, Email: ${result.email}`);
                    $form[0].reset();
                    fetchUserList(role);
                } else {
                    alert(`Error: ${result.message}`);
                }
            },
            error: function (error) {
                console.error('Error:', error);
                alert('An error occurred while adding the user.');
            },
            complete: function () {
                console.log('Submission process completed');
                isSubmitting = false;
            }
        });

        return false;
    };

    window.handleBulkUpload = function(event) {
        event.preventDefault();
        console.log('Bulk upload attempt');

        if (isSubmitting) {
            console.log('Submission already in progress, ignoring');
            return false;
        }

        isSubmitting = true;
        console.log('Starting bulk upload process');

        const $form = $(event.target);
        const formData = new FormData($form[0]);

        $.ajax({
            url: '/admin/bulk_upload_users',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (result) {
                if (result.success) {
                    alert(result.message);
                    fetchUserList('student');
                    fetchUserList('staff');
                } else {
                    alert('Error: ' + result.message);
                }
            },
            error: function (error) {
                console.error('Error:', error);
                alert('An error occurred while uploading the file.');
            },
            complete: function () {
                console.log('Bulk upload process completed');
                isSubmitting = false;
            }
        });

        return false;
    };

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
        $.ajax({
            url: `/admin/get_users/${role}`,
            method: 'GET',
            success: function (result) {
                if (result.success) {
                    const tableId = `#${role}Table`;
                    const table = $(tableId).DataTable();

                    table.clear();

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

                    table.draw();
                } else {
                    console.error(`Error fetching ${role} list:`, result.message);
                }
            },
            error: function (error) {
                console.error(`Error fetching ${role} list:`, error);
            }
        });
    }

    // Initialize DataTables
    if ($('#studentTable').length) {
        studentTable = $('#studentTable').DataTable();
    }
    if ($('#staffTable').length) {
        staffTable = $('#staffTable').DataTable();
    }

    // Fetch initial data
    fetchUserList('student');
    fetchUserList('staff');

    // Event delegation for toggle status and reset password buttons
    $(document).on('click', '.toggle-status', function () {
        const username = $(this).data('username');
        const role = $(this).data('role');
        toggleUserStatus(username, role);
    });

    $(document).on('click', '.reset-password', function () {
        const username = $(this).data('username');
        const role = $(this).data('role');
        resetUserPassword(username, role);
    });

    function toggleUserStatus(username, role) {
        $.ajax({
            url: '/admin/toggle_user_status',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ username, role }),
            success: function (result) {
                if (result.success) {
                    alert(`User status updated successfully.`);
                    fetchUserList(role);
                } else {
                    alert(`Error: ${result.message}`);
                }
            },
            error: function (error) {
                console.error('Error:', error);
                alert('An error occurred while updating user status.');
            }
        });
    }

    function resetUserPassword(username, role) {
        $.ajax({
            url: '/admin/reset_user_password',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ username, role }),
            success: function (result) {
                if (result.success) {
                    alert(`Password reset successfully. New password: ${result.password}`);
                } else {
                    alert(`Error: ${result.message}`);
                }
            },
            error: function (error) {
                console.error('Error:', error);
                alert('An error occurred while resetting the password.');
            }
        });
    }

    // Remove the old event listener for bulk upload
    // $('#bulk-upload-form').off('submit');

    // ... rest of the existing code ...
});