$(document).ready(function () {
    loadBlocks();
    loadStudents();
    loadAllRoomAssignments();
    loadRoomChangeRequests();

    $('#assign-room-form').submit(assignRoom);
    $('#block-select').change(loadFloors);
    $('#floor-select').change(loadAvailableRooms);
    $('#add-block-form').submit(addBlock);

    $('#add-floor-btn').click(function () {
        const floorsContainer = $('#edit-floors-container');
        const floorIndex = floorsContainer.children().length;
        addFloorInputs(floorsContainer, floorIndex);
    });

    $('#save-block-changes').click(function () {
        const blockId = $('#edit-block-id').val();
        const blockName = $('#edit-block-name').val();
        const floors = [];

        $('.floor-card').each(function (index, floorCard) {
            const floor = {};
            $(floorCard).find('input').each(function () {
                const name = $(this).attr('name');
                const value = $(this).val();
                const key = name.match(/\[(\w+)\]$/)[1];
                floor[key] = value;
            });
            floors.push(floor);
        });

        const data = {
            blockId: blockId,
            blockName: blockName,
            floors: floors
        };

        $.ajax({
            url: '/admin/update_block',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function (response) {
                if (response.success) {
                    alert('Block updated successfully');
                    $('#editBlockModal').modal('hide');
                    loadBlocks();
                } else {
                    alert('Failed to update block: ' + response.message);
                }
            }
        });
    });

    // Submit room change request
    $('#room-change-form').submit(function(e) {
        e.preventDefault();
        const blockId = $('#block-select').val();
        const floorIndex = $('#floor-select').val();
        const roomNumber = $('#room-select').val();
        const reason = $('#reason').val();

        const requestData = {
            blockId: blockId,
            floorIndex: parseInt(floorIndex, 10),
            roomNumber: roomNumber,
            reason: reason
        };

        $.ajax({
            url: '/student/request_room_change',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(requestData),
            success: function(response) {
                if (response.success) {
                    alert('Room change request submitted successfully.');
                    $('#room-change-form')[0].reset();
                    loadRoomChangeStatus();
                } else {
                    alert('Error submitting room change request: ' + response.message);
                }
            },
            error: function(xhr, status, error) {
                alert('Error submitting room change request. Please try again later.');
            }
        });
    });

    function loadRoomChangeStatus() {
        $.ajax({
            url: '/student/get_room_change_status',
            type: 'GET',
            success: function(response) {
                if (response.success) {
                    if (response.request) {
                        $('#room-change-status').html(`
                            <p><strong>Status:</strong> ${response.request.status}</p>
                            <p><strong>Requested Room:</strong> ${response.request.room_number} (Block ${response.request.block_name}, Floor ${response.request.floor_index + 1})</p>
                            <p><strong>Reason:</strong> ${response.request.reason}</p>
                            ${response.request.admin_note ? `<p><strong>Admin Note:</strong> ${response.request.admin_note}</p>` : ''}
                        `);
                    } else {
                        $('#room-change-status').html('<p>No active room change request.</p>');
                    }
                } else {
                    $('#room-change-status').html('<p>Error: ' + response.message + '</p>');
                }
            },
            error: function(xhr, status, error) {
                $('#room-change-status').html('<p>Error loading room change status. Please try again later.</p>');
            }
        });
    }

    loadRoomChangeStatus();
});

function loadBlocks() {
    console.log("Loading blocks...");
    $.get('/admin/get_blocks', function (response) {
        console.log("Received raw response:", response);
        if (response.success) {
            console.log("Blocks loaded successfully:", response.blocks);
            populateBlockDropdown(response.blocks);
            displayBlocks(response.blocks);
        } else {
            console.error("Failed to load blocks:", response.message);
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("AJAX request failed:", textStatus, errorThrown);
    });
}

function populateBlockDropdown(blocks) {
    const blockSelect = $('#block-select');
    blockSelect.empty().append('<option value="">Select Block</option>');
    blocks.forEach(block => {
        blockSelect.append(`<option value="${block._id}">${block.name}</option>`);
    });
}

function displayBlocks(blocks) {
    console.log("Displaying blocks:", blocks);
    const blockList = $('#block-list');
    blockList.empty();
    
    if (!blocks || blocks.length === 0) {
        console.log("No blocks to display");
        blockList.append('<p>No blocks available.</p>');
        return;
    }
    
    blocks.forEach(block => {
        console.log("Processing block:", JSON.stringify(block, null, 2));
        let totalRooms = 0;
        let floorCount = 0;
        if (block.floors && Array.isArray(block.floors)) {
            floorCount = block.floors.length;
            totalRooms = block.floors.reduce((sum, floor) => {
                console.log("Processing floor:", floor);
                return sum + parseInt(floor.singleRooms || 0) + 
                             parseInt(floor.doubleRooms || 0) + 
                             parseInt(floor.tripleRooms || 0);
            }, 0);
        } else {
            console.warn("Block doesn't have a valid floors array:", block);
        }
        
        const blockHtml = `
            <div class="card mb-3 block-card" data-block-name="${block.name ? block.name.toLowerCase() : ''}">
                <div class="card-header">
                    <h4>${block.name || 'Unnamed Block'}</h4>
                </div>
                <div class="card-body">
                    <p><strong>Total Floors:</strong> ${floorCount}</p>
                    <p><strong>Total Rooms:</strong> ${totalRooms}</p>
                    <button class="btn btn-primary btn-sm" onclick="editBlock('${block._id}')">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteBlock('${block._id}')">Delete</button>
                </div>
            </div>
        `;
        console.log("Appending block HTML:", blockHtml);
        blockList.append(blockHtml);
    });

    // Add search functionality
    $('#block-search').on('input', function () {
        const searchTerm = $(this).val().toLowerCase();
        $('.block-card').each(function () {
            const blockName = $(this).data('block-name');
            if (blockName && blockName.includes(searchTerm)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });
}

function loadFloors() {
    const blockId = $('#block-select').val();
    if (blockId) {
        $.get(`/admin/get_floors/${blockId}`, function (response) {
            if (response.success) {
                populateFloorDropdown(response.floors);
            }
        });
    } else {
        $('#floor-select').empty().append('<option value="">Select Floor</option>');
        $('#room-select').empty().append('<option value="">Select Room</option>');
    }
}

function loadAvailableRooms() {
    const blockId = $('#block-select').val();
    const floorIndex = $('#floor-select').val();
    if (blockId && floorIndex !== '') {
        $.get(`/admin/get_available_rooms/${blockId}/${floorIndex}`, function (response) {
            if (response.success) {
                populateRoomDropdown(response.rooms);
            }
        });
    } else {
        $('#room-select').empty().append('<option value="">Select Room</option>');
    }
}

function loadStudents() {
    $.get('/admin/get_unassigned_students', function (response) {
        if (response.success) {
            populateStudentDropdown(response.students);
        }
    });
}

function assignRoom(e) {
    e.preventDefault();
    const blockId = $('#block-select').val();
    const floorIndex = $('#floor-select').val();
    const roomNumber = $('#room-select').val();
    const studentId = $('#student-select').val();
    const roomType = $('#room-select option:selected').data('type');
    const isAttached = $('#room-select option:selected').data('attached');

    if (!blockId || floorIndex === '' || !roomNumber || !studentId || !roomType) {
        alert('Please select all fields');
        return;
    }

    const data = { blockId, floorIndex, roomNumber, studentId, roomType, isAttached };

    $.ajax({
        url: '/admin/assign_room',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function (response) {
            if (response.success) {
                alert('Room assigned successfully');
                loadStudents();
                loadAvailableRooms();
                loadAllRoomAssignments();
            } else {
                alert('Failed to assign room: ' + response.message);
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.error('Error:', textStatus, errorThrown);
            alert('An error occurred while assigning the room: ' + jqXHR.responseText);
        }
    });
}

function loadAllRoomAssignments() {
    $.get('/admin/get_all_room_assignments', function (response) {
        if (response.success) {
            const allAssignmentsList = $('#all-room-assignments');
            allAssignmentsList.empty();
            response.assignments.forEach(assignment => {
                allAssignmentsList.append(`
                    <tr>
                        <td>${assignment.block_name}</td>
                        <td>${assignment.room_number}</td>
                        <td>${assignment.room_type}</td>
                        <td>${assignment.student_name}</td>
                        <td>${assignment.occupants}/${assignment.capacity}</td>
                        <td>
                            <button class="btn btn-danger btn-sm" onclick="unassignRoom('${assignment._id}')">Unassign</button>
                        </td>
                    </tr>
                `);
            });
        }
    });
}

function unassignRoom(assignmentId) {
    if (confirm('Are you sure you want to unassign this room?')) {
        $.ajax({
            url: `/admin/unassign_room/${assignmentId}`,
            method: 'POST',
            success: function (response) {
                if (response.success) {
                    alert('Room unassigned successfully');
                    loadStudents();
                    loadAllRoomAssignments();
                } else {
                    alert('Failed to unassign room: ' + response.message);
                }
            }
        });
    }
}

function populateFloorDropdown(floors) {
    const floorSelect = $('#floor-select');
    floorSelect.empty().append('<option value="">Select Floor</option>');
    floors.forEach((floor, index) => {
        floorSelect.append(`<option value="${index}">${index + 1}</option>`);
    });
}

function populateRoomDropdown(rooms) {
    const roomSelect = $('#room-select');
    roomSelect.empty().append('<option value="">Select Room</option>');
    rooms.forEach(room => {
        const attachedText = room.attached ? 'Attached' : 'Non-attached';
        roomSelect.append(`<option value="${room.number}" data-type="${room.type}" data-attached="${room.attached}">
            ${room.number} (${room.type}, ${attachedText})
        </option>`);
    });
}

function populateStudentDropdown(students) {
    const studentSelect = $('#student-select');
    studentSelect.empty().append('<option value="">Select Student</option>');
    students.forEach(student => {
        studentSelect.append(`<option value="${student._id}">${student.full_name}</option>`);
    });
}

function addBlock(e) {
    e.preventDefault();
    const blockName = $('#block-name').val();
    const floorCount = $('#floor-count').val();

    if (!blockName || !floorCount) {
        alert('Please fill in all fields');
        return;
    }

    const data = {
        blockName: blockName,
        floors: Array(parseInt(floorCount)).fill().map(() => ({
            singleRooms: 0,
            doubleRooms: 0,
            tripleRooms: 0,
            singleAttachedRooms: 0,
            doubleAttachedRooms: 0,
            tripleAttachedRooms: 0
        }))
    };


    $.ajax({
        url: '/admin/add_block',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function (response) {
            if (response.success) {
                alert('Block added successfully');
                $('#block-name').val('');
                $('#floor-count').val('');
                loadBlocks();
            } else {
                alert('Failed to add block: ' + response.message);
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error('Error:', textStatus, errorThrown);
            console.log('Response:', jqXHR.responseText);
            alert('An error occurred while adding the block. Please check the console for more details.');
        }
    });
}

function editBlock(blockId) {
    $.get(`/admin/get_block/${blockId}`, function (response) {
        if (response.success) {
            const block = response.block;
            $('#edit-block-id').val(block._id);
            $('#edit-block-name').val(block.name);

            const floorsContainer = $('#edit-floors-container');
            floorsContainer.empty();

            block.floors.forEach((floor, index) => {
                addFloorInputs(floorsContainer, index, floor);
            });

            $('#editBlockModal').modal('show');
        } else {
            alert('Failed to load block details');
        }
    });
}

function addFloorInputs(container, floorIndex, floorData = {}) {
    const floorHtml = `
        <div class="card mb-3 floor-card">
            <div class="card-header">
                <h5>Floor ${floorIndex + 1}</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Single Rooms</label>
                        <input type="number" class="form-control" name="floors[${floorIndex}][singleRooms]" value="${floorData.singleRooms || 0}" min="0">
                    </div>
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Double Rooms</label>
                        <input type="number" class="form-control" name="floors[${floorIndex}][doubleRooms]" value="${floorData.doubleRooms || 0}" min="0">
                    </div>
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Triple Rooms</label>
                        <input type="number" class="form-control" name="floors[${floorIndex}][tripleRooms]" value="${floorData.tripleRooms || 0}" min="0">
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Single Rooms with Attached Toilet</label>
                        <input type="text" class="form-control" name="floors[${floorIndex}][singleAttachedRoomNumbers]" value="${floorData.singleAttachedRoomNumbers || ''}" placeholder="e.g., 101, 102, 103">
                    </div>
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Double Rooms with Attached Toilet</label>
                        <input type="text" class="form-control" name="floors[${floorIndex}][doubleAttachedRoomNumbers]" value="${floorData.doubleAttachedRoomNumbers || ''}" placeholder="e.g., 201, 202, 203">
                    </div>
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Triple Rooms with Attached Toilet</label>
                        <input type="text" class="form-control" name="floors[${floorIndex}][tripleAttachedRoomNumbers]" value="${floorData.tripleAttachedRoomNumbers || ''}" placeholder="e.g., 301, 302, 303">
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Single Rooms without Attached Toilet</label>
                        <input type="text" class="form-control" name="floors[${floorIndex}][singleNonAttachedRoomNumbers]" value="${floorData.singleNonAttachedRoomNumbers || ''}" placeholder="e.g., 104, 105, 106">
                    </div>
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Double Rooms without Attached Toilet</label>
                        <input type="text" class="form-control" name="floors[${floorIndex}][doubleNonAttachedRoomNumbers]" value="${floorData.doubleNonAttachedRoomNumbers || ''}" placeholder="e.g., 204, 205, 206">
                    </div>
                    <div class="col-md-4 mb-2">
                        <label class="form-label">Triple Rooms without Attached Toilet</label>
                        <input type="text" class="form-control" name="floors[${floorIndex}][tripleNonAttachedRoomNumbers]" value="${floorData.tripleNonAttachedRoomNumbers || ''}" placeholder="e.g., 304, 305, 306">
                    </div>
                </div>
            </div>
        </div>
    `;
    container.append(floorHtml);
}

function deleteBlock(blockId) {
    if (confirm('Are you sure you want to delete this block? This action cannot be undone.')) {
        $.ajax({
            url: `/admin/delete_block/${blockId}`,
            method: 'POST',
            success: function (response) {
                if (response.success) {
                    alert('Block deleted successfully');
                    loadBlocks();
                } else {
                    alert('Failed to delete block: ' + response.message);
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.error('Error:', textStatus, errorThrown);
                alert('An error occurred while deleting the block');
            }
        });
    }
}

function loadRoomChangeRequests() {
    $.get('/admin/get_room_change_requests', function (response) {
        if (response.success) {
            const requestsList = $('#room-change-requests-list');
            requestsList.empty();
            response.requests.forEach(request => {
                requestsList.append(`
                    <tr>
                        <td>${request.student_name}</td>
                        <td>${request.current_room}</td>
                        <td>${request.requested_room}</td>
                        <td>${request.reason}</td>
                        <td>${request.status}</td>
                        <td>
                            <button class="btn btn-success btn-sm" onclick="processRoomChangeRequest('${request._id}', 'approve')">Approve</button>
                            <button class="btn btn-danger btn-sm" onclick="processRoomChangeRequest('${request._id}', 'reject')">Reject</button>
                        </td>
                    </tr>
                `);
            });
        }
    });
}

function processRoomChangeRequest(requestId, action) {
    const adminNote = prompt(`Enter a note for ${action}ing this request:`);
    if (adminNote === null) return;

    $.ajax({
        url: '/admin/process_room_change_request',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ requestId, action, adminNote }),
        success: function (response) {
            if (response.success) {
                alert(`Request ${action}ed successfully`);
                loadRoomChangeRequests();
            } else {
                alert(`Failed to ${action} request: ${response.message}`);
            }
        }
    });
}