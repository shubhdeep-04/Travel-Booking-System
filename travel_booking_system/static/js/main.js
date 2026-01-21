// Main JavaScript file
$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Date picker initialization
    $('input[type="date"]').each(function() {
        var today = new Date().toISOString().split('T')[0];
        var minDate = this.getAttribute('min');
        
        if (!minDate) {
            $(this).attr('min', today);
        }
    });
    
    // Price range slider
    $('input[type="range"]').on('input', function() {
        var value = $(this).val();
        $(this).next('.range-value').text('$' + value);
    });
    
    // Form validation
    $('form').on('submit', function() {
        var submitBtn = $(this).find('button[type="submit"]');
        submitBtn.prop('disabled', true);
        submitBtn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...');
    });
    
    // Auto-calculate booking totals
    $('.booking-calc').on('change', function() {
        calculateBookingTotal();
    });
    
    // Seat selection
    $('.seat.available').on('click', function() {
        $(this).toggleClass('selected');
        updateSelectedSeats();
    });
    
    // Image gallery
    $('.gallery-thumb').on('click', function() {
        var imgSrc = $(this).data('full');
        $('#mainImage').attr('src', imgSrc);
    });
    
    // Booking calendar
    $('.calendar-day').on('click', function() {
        $('.calendar-day').removeClass('selected');
        $(this).addClass('selected');
        var date = $(this).data('date');
        $('#selectedDate').val(date);
    });
    
    // Search autocomplete
    $('#searchInput').on('keyup', function() {
        var query = $(this).val();
        if (query.length > 2) {
            fetchAutocompleteSuggestions(query);
        }
    });
    
    // Wallet top-up
    $('.topup-amount').on('click', function() {
        var amount = $(this).data('amount');
        $('#topupAmount').val(amount);
    });
    
    // Payment method selection
    $('.payment-method').on('click', function() {
        $('.payment-method').removeClass('active');
        $(this).addClass('active');
        var method = $(this).data('method');
        $('#paymentMethod').val(method);
    });
});

// Functions
function calculateBookingTotal() {
    var nights = $('#nights').val() || 0;
    var rooms = $('#rooms').val() || 1;
    var price = $('#pricePerNight').val() || 0;
    var total = nights * rooms * price;
    $('#totalAmount').text('$' + total.toFixed(2));
}

function updateSelectedSeats() {
    var selectedSeats = [];
    $('.seat.selected').each(function() {
        selectedSeats.push($(this).data('seat'));
    });
    $('#selectedSeats').val(selectedSeats.join(','));
    $('#seatCount').text(selectedSeats.length);
}

function fetchAutocompleteSuggestions(query) {
    $.ajax({
        url: '/api/autocomplete/',
        data: { q: query },
        success: function(data) {
            updateAutocompleteResults(data.results);
        }
    });
}

function updateAutocompleteResults(results) {
    var html = '';
    results.forEach(function(item) {
        html += '<div class="autocomplete-item">' + item.text + '</div>';
    });
    $('#autocompleteResults').html(html).show();
}

// Chart initialization
function initRevenueChart() {
    const ctx = document.getElementById('revenueChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Revenue',
                    data: [12000, 19000, 15000, 25000, 22000, 30000],
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                }
            }
        });
    }
}

// Booking status update
function updateBookingStatus(bookingId, status) {
    $.ajax({
        url: '/api/bookings/' + bookingId + '/status/',
        method: 'POST',
        data: { status: status },
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        success: function(response) {
            if (response.success) {
                location.reload();
            }
        }
    });
}

// Utility function to get CSRF token
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Initialize when document is ready
$(document).ready(function() {
    initRevenueChart();
    
    // Set minimum dates for booking forms
    var today = new Date().toISOString().split('T')[0];
    $('.date-min-today').attr('min', today);
    
    var tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    $('.date-min-tomorrow').attr('min', tomorrow.toISOString().split('T')[0]);
});