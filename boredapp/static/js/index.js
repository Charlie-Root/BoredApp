
// Get the alert element
var alertElement = document.getElementById('alert-message');

// Set a timeout to remove the alert after 3 seconds
setTimeout(function() {
        alertElement.remove();
    }, 2500);