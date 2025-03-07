document.addEventListener('DOMContentLoaded', function() {
    // Check page
    const title = document.title;
    console.log(title);

    if (document.title.includes('StandIn | Django site admin')) {
        console.log('This is the StandIn admin page');
        format_standin_admin();
    }

})

function format_standin_admin() {

    // Format Images Section
    const main_image_div = document.querySelector('.field-display_main_image');
    const field_list_uploads_div = document.querySelector('.field-list_uploads');

    if (field_list_uploads_div) {
        const readonlyDiv = field_list_uploads_div.querySelector('.readonly');
        if (readonlyDiv) {
            readonlyDiv.classList.remove('readonly');
        }
    }

    main_image_div.innerHTML += field_list_uploads_div.innerHTML;
    field_list_uploads_div.remove();
    const fieldsets = document.querySelectorAll('.col');

    // Format fieldsets
    document.getElementsByTagName("fieldset")[0].parentElement.classList.add("fieldsets");

    document.querySelector(".submit-row").classList.add("col", "col6");

    // fieldsets.forEach(fieldset => {
    //     if (fieldset.classList.contains('col2')) {
    //         fieldset.style.gridColumn = "span 2"; // Takes 2 out of 6 columns
    //     } else if (fieldset.classList.contains('col3')) {
    //         fieldset.style.gridColumn = "span 3"; // Takes 3 out of 6 columns
    //     }
    // });
}