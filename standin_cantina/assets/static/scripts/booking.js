document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded');
    const templateType = document.body.getAttribute("data-template");
    const user_id = document.body.getAttribute("data-user");

    // Add event listener for nav links
    load_nav();

    // Clear messages
    clear_messages();

    //switch View to home by default
    switch (templateType) {
        case 'home':
            view_switcher('home');
            break;
        case 'index':
            view_switcher('index');
            break;
        case 'standin':
            load_availchecks(user_id);
            view_switcher('standin');
            break;
    }
});


// Clear messages
function clear_messages() {
    const message = document.querySelector('.message');
    if (message) {
        message.innerHTML = '';
    }
}


function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        .split('=')[1];
    return cookieValue;
}


function load_nav() {
    document.querySelectorAll('.nav-link').forEach(nav_link => {
        if (nav_link.dataset.view != 'logout') {
            nav_link.addEventListener('click', (event) => {
                event.preventDefault();
                switch (nav_link.dataset.view) {
                    case 'home':
                        load_home();
                        break;
                    case 'register_user':
                        load_register_user();
                        break;
                    case 'register_standin':
                        load_register_standin();
                        break;
                    case 'registration_pending':
                        break;
                    case 'login':
                        load_login();
                        break;
                    case 'user_account':
                        load_user_account();
                        break;
                    case 'standin_profile':
                        load_standin_profile();
                        break;
                }
                view_switcher(nav_link.dataset.view);
            });
        }
    })
}


function view_switcher(view) {
    console.log(`In view_switcher. view = ${view}`);
    // Validate view parameter
    if (!['home', 'user_account', 'Stand-in_profile', 'register_user', 'register_standin', 'registration_pending', 'login', 'logout', 'bookings', 'availchecks', 'availabilities'].includes(view)) {
        console.log(`index_view_switcher could not figure out which view is ${view}`);
        return;
    }

    // Hide all views
    document.querySelectorAll('.view').forEach(view_div => {
        view_div.style.display = 'none';
    });

    // Clear any messages
    clear_messages();

    // Show appropriate views
    if (document.querySelector(`#${view}-view`)) {
        document.querySelector(`#${view}-view`).style.display = 'block';
    }

    if (view === 'availchecks') {
        document.querySelector(`#bookings-view`).style.display = 'block';
        document.querySelector(`#availabilities-view`).style.display = 'block';
    }
}


function load_home() {
    clear_messages();

    // Clear the pHeading
    document.querySelector('#pHeading').innerHTML = '';

    view_switcher('home');
}


function fixStandInCheckbox() {
    // fix is_standin check box
    const is_standin_input = document.querySelector('#id_is_standin');
    if (!is_standin_input) return;

    const is_standin_div = is_standin_input.parentElement;
    is_standin_div.classList.add('checkbox_parent')

    const new_div = document.createElement('div');
    new_div.classList.add('checkbox_label_div');

    const childrenArray = Array.from(is_standin_div.children);

    childrenArray.forEach(child => {
        if (child !== is_standin_input) {
            new_div.appendChild(child);
        }
    });
    is_standin_div.innerHTML= '';
    is_standin_div.append(is_standin_input);
    is_standin_div.append(new_div);
}


async function load_register_user() {

    console.log(`In load_register_user()`);

    clear_messages();

    document.querySelector('#pHeading').innerHTML = `User registration`;
    const view = document.querySelector('#register_user-view');
    view.innerHTML = `
        <div class='form-view'>
            <form>
                <div id='userRegistration_form' class='col-md-5'></div>
                <button id='regUser_btn' type='submit'>Next</button>
            </form>
            Already have an account? <a id='login_link' class='login' data-view="login" href=''>Log In here.</a>
        </div>`;

    const login_link = document.querySelector('#login_link')
    login_link.addEventListener('click', event => {
        event.preventDefault();
        load_login();
        view_switcher('login');
    })

    const userRegistration_form = document.querySelector('#userRegistration_form');

    await fetch(`register_user`, {
            method: 'GET',
            headers: {
                'content-type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            //Add form
            userRegistration_form.innerHTML = data.user_reg_form;
        })
        .catch(error => console.error("Error loading form:", error));
        console.log(`userRegistration_form.innerHTML = ${userRegistration_form.innerHTML}`);
        strap_up(userRegistration_form);

    fixStandInCheckbox();

    // Add 'Next' button event listener
    const button = document.getElementById("regUser_btn")
    button.classList.add('btn', 'btn-primary');
    button.addEventListener("click", function(event) {
        event.preventDefault();

        let reg_form = userRegistration_form.parentElement; // Select the form element

        if (reg_form.checkValidity()) {
            handle_regUser_btn(); // Proceed with AJAX submission
        } else {
            reg_form.reportValidity(); // Show validation messages
        }
    });
}


async function handle_regUser_btn() {

    let userReg_form = document.querySelector("#userRegistration_form").parentElement;
    console.log(userReg_form.innerHTML)
    let userReg_formData = new FormData(userReg_form);
    const message = document.querySelector(".message");
    const is_standin = document.getElementsByName('is_standin')[0].checked;

    await fetch(`register_user`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
            },
            body: userReg_formData
        })
        .then(response => response.json())
        .then(result => {
            // Print result
            console.log(result, result.message);

            // Populate message
            message.innerHTML = result.message;
            message.classList.add(`${result.status}_message`);

            // If success response will be {'user': value, 'status': 'success', 'message':'User created successfully'}
            if (result.status === 'success') {
                if (is_standin) {
                    load_register_standin(result.user);
                } else {
                    load_reg_pending();
                }
            }

            // Failure, response = {'status': 'error', 'message': value, 'bungler': value}
            if (result.status === 'error') {
                Object.keys(result.errors).forEach(key => {
                    result.errors[key].forEach(error => {
                        console.log(`${key}: ${error}`);
                    });
                });
            }
        })
        .catch(error => {
            // Handle any errors that occurred during the fetch or processing
            console.error('Error logging in:', error);
        });
}


async function load_register_standin(user) {
    document.querySelector('#pHeading').innerHTML = 'Stand-in registration';
    let view = document.querySelector('#register_standin-view');
    view.innerHTML = `
        <form>
            <div class="form-group col-md-5">
                <div id='standInRegistration_form'>
                </div>
            </div>
            <button id='regStandIn_btn' type='submit'>Submit</button>
        </form>`;

    const standInRegistration_form = document.querySelector('#standInRegistration_form');

    try {
        let response = await fetch(`register_standin/${user.id}`, {
            method: 'GET',
            headers: {
                'content-type': 'application/json',
            }
        });

        console.log(response);

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        let data = await response.json();

        // Ensure form data exists before updating innerHTML
        if (data.standin_reg_form) {
            standInRegistration_form.innerHTML = data.standin_reg_form;
        } else {
            console.error("Error: standin_reg_form is missing in response.");
        }
    } catch (error) {
        console.error("Error loading form:", error);
    }

    strap_up(standInRegistration_form);

    // Ensure button exists before adding event listener
    let button = document.getElementById("regStandIn_btn");
    if (button) {
        button.classList.add('btn');
        button.addEventListener("click", function(event) {
            event.preventDefault();
            handle_regStandIn_btn(user);
        });
    } else {
        console.error("Error: regStandIn_btn not found.");
    }

    // Switch to the register_standin view
    view_switcher('register_standin');
}


async function handle_regStandIn_btn(user) {

    let standInReg_form = document.querySelector("#standInRegistration_form").parentElement.parentElement;
    let standInReg_formData = new FormData(standInReg_form);
    const message = document.querySelector('.message');

    await fetch(`register_standin/${user.id}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
            },
            body: standInReg_formData
        })
        .then(response => response.json())
        .then(result => {
            // Print result
            console.log(result, result.message);

            // Populate message
            if (message) {
                message.innerHTML = result.message;
            }

            // If success response will be {'user': value, 'status': 'success', 'message':'Stand-in created successfully'}
            if (result.status === 'success') {
                    load_reg_pending();
            }

            // Failure, response = {'status': 'error', 'message': value, 'bungler': value}
            if (result.status === 'error') {
                Object.keys(result.errors).forEach(key => {
                    result.errors[key].forEach(error => {
                        console.log(`${key}: ${error}`);
                    });
                });
            }
        })
        .catch(error => {
            // Handle any errors that occurred during the fetch or processing
            console.error('Error registering stand-in:', error);
        });
}

// Add bootstrap classes
function strap_up(form) {
    Array.from(form.children).forEach(div => {
        div.classList.add('form-group');
        Array.from(div.children).forEach(element => {
            if (element.tagName === 'LABEL') {
                element.classList.add('form-label');
            }
            if (element.tagName === 'INPUT') {
                check_required(element);
                element.classList.add('form-control');
                if (element.type === 'checkbox') {
                    element.classList.add('form-check-input');
                }
            }
        })
    });
}


function check_required(element) {
    console.log(`In check_required() element = ${element.outerHTML}`);
    if (element.hasAttribute("required")) {
        let label = element.parentElement.firstElementChild;
        let span = document.createElement('span');
        span.textContent = " *";
        span.style.color = "red";
        label.appendChild(span);
    }
}


function load_reg_pending() {
    document.querySelector('#pHeading').innerHTML = 'Registration pending';
    view_switcher('registration_pending');
}


function load_login() {
    document.querySelector('#pHeading').innerHTML = `Login`;
    document.querySelector('#login-view').innerHTML = `
        <form id='login_form'>
            <div class="form-group">
                <input class="form-control" type="text" name="username" placeholder="Username" autofocus autocomplete="username">
            </div>
            <div class="form-group">
                <input class="form-control" type="password" name="password" placeholder="Password" autocomplete="current-password">
            </div>
            <input id='login_btn' class="btn btn-primary" type="submit" value="Login">
        </form>

        Don't have an account? <a id='register_link' class='register' href="">Register here.</a>`;

    $("#login_btn").click((event) => {
        event.preventDefault();
        handle_login();
    })

    document.querySelector('#register_link').onclick = (event) => {
        event.preventDefault();
        load_register_user();
        view_switcher('register_user');
    }
}


async function handle_login() {

    let login_form = document.querySelector("#login_form");
    let login_formData = new FormData(login_form);
    const message = document.querySelector("#message");

    fetch(`login`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
            },
            body: login_formData
        })
        .then(response => {
            // If the response is HTML (for successful login), replace the current document
            if (response.headers.get('content-type').includes('text/html')) {
                return response.text().then(location.reload());
            }

            // Otherwise, assume JSON response (for failed login)
            return response.json().then(result => {
                // Print result
                console.log(result, result.message);

                // Populate message
                message.innerHTML = result.message;

                if (result.status == 'error') {
                    Object.keys(result.errors).forEach(key => {
                        result.errors[key].forEach(error => {
                            message.innerHTML += `<p>${error}</p>`;
                        });
                    });
                }
            });
        })
        .catch(error => {
            // Handle any errors that occurred during the fetch or processing
            console.error('Error loggin in:', error);
            message.innerHTML += 'Error loggin in';
        });
}

function load_user_account() {
    document.querySelector('#pHeading').innerHTML = 'User Account';

}


async function load_standin_profile() {

    //Set Page heading
    document.querySelector('#pHeading').innerHTML = `Stand-in Profile`;
    document.querySelector('#standinProfile-view').innerHTML = `
        <form id='updateProfile_form'>
            <div class="form-group col-md-5">
                <div id='standinForm'>

                </div>
            </div>
            <input id='updateProfile_btn' class="btn btn-primary" type="submit" value="Update">
        </form>`;

    // Add Profile button event listener
    $("#updateProfile_btn").click((event) => {
        event.preventDefault();
        update_profile();
    })

    // Show profile view and hide other views
    view_switcher('userProfile');

    let profile_form;
    await fetch(`profile`, {
            method: 'GET',
            headers: {
                'content-type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            user = data.user;
            profile_form = data.profile_form;
        })

    //Add form
    document.querySelector('#userForm').innerHTML = profile_form;
    document.querySelectorAll('#id_delete_profile_pic').forEach(child => {
        child.parentElement.classList.add('checkBox_div');
    });

}


async function update_standin_profile() {

    let profile_form = document.querySelector("#updateProfile_form");
    let profile_formData = new FormData(profile_form);

    await fetch(`profile`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
            },
            body: profile_formData
        })
        .then(response => response.json())
        .then(result => {
            // Print result
            console.log(result, result.message, result.errors);

            // Check if the profile was updated successfully
            const message = document.querySelector("#message")
            if (result.status === 'success') {
                message.innerHTML = result.message;
            } else {
                Object.keys(result.errors).forEach(key => {
                    message.innerHTML += result.errors[key][0];
                })
                return;
            }
        })
        .catch(error => {
            // Handle any errors that occurred during the fetch or processing
            console.error('Error updating profile:', error);
        });
}


async function load_availchecks(user_id) {
    await fetch(`load_availchecks/${user_id}`, {
        method: 'GET',
        headers: {
            'content-type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);

        // Create container for all AvailChecks
        const avail_checks_div = document.createElement('div');
        avail_checks_div.setAttribute('class', 'avail_checks_div container');
        
        // Create ul to list all AvailChecks
        const avail_checks_ul = document.createElement('ul');
        avail_checks_ul.setAttribute('class', 'avail_checks_ul');
        avail_checks_ul.setAttribute('id', 'avail_checks_ul');
        avail_checks_div.appendChild(avail_checks_ul);

        // Iterate over queryset
        data.forEach(avail_check => {

            // Create li for each AvailCheck
            const avail_check_li = document.createElement('li');
            avail_check_li.setAttribute('class', 'avail_check_li');
            avail_check_li.setAttribute('id', `avail_check_li_${avail_check.pk}`);
            avail_checks_ul.appendChild(avail_check_li);

            // Create Accept Avail Check Button
            const accept_btn = document.createElement('button');
            accept_btn.id = `accept_${avail_check['id']}`;
            accept_btn.classList = 'btn accept_btn';
            accept_btn.addEventListener('click', accept_availcheck(avail_check['id'])) 

            // Create Reject Avail Check Button
            const reject_btn = document.createElement('button');
            reject_btn.id = `reject_${avail_check['id']}`;
            reject_btn.classList = 'btn reject_btn';
            reject_btn.addEventListener('click', reject_availcheck(avail_check['id'])) 
        })
    })
}


async function accept_availcheck(avail_check_id) {
    if (confirm("Accept Avail Check?")) {
        await fetch(`accept_availcheck/${avail_check_id}`, {
            method: 'GET',
            headers: {
                'content-type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            // TO DO:
            // If accept succeds make button light up and disabled
            const accept_btn = document.querySelector(`#accept_${avail_check_id}`);
            accept_btn.classList.add('disabled');
            accept_btn.attributes.add('disabled');
            // else display failure message
        });
    }
}


async function reject_availcheck(avail_check_id) {}