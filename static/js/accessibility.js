/**
 * Accessibility features for Fireflies
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load user accessibility settings
    loadAccessibilitySettings();
    
    // Add keyboard navigation detection
    detectKeyboardNavigation();
    
    // Add keyboard shortcuts
    setupKeyboardShortcuts();
});

/**
 * Load user accessibility settings from localStorage or server
 */
function loadAccessibilitySettings() {
    // Try to load from localStorage first (for immediate effect)
    const darkMode = localStorage.getItem('dark_mode') === 'true';
    const highContrast = localStorage.getItem('high_contrast') === 'true';
    const reducedMotion = localStorage.getItem('reduced_motion') === 'true' || localStorage.getItem('reduce_animations') === 'true';
    const textSize = localStorage.getItem('font_size') || localStorage.getItem('text_size') || '100';
    const fontFamily = localStorage.getItem('font_family') || 'system-ui';
    const dyslexiaFont = localStorage.getItem('dyslexia_font') === 'true';
    const lineSpacing = localStorage.getItem('line_spacing') || '1.5';
    const enhancedA11y = localStorage.getItem('enhanced_a11y') === 'true';
    const focusMode = localStorage.getItem('focus_mode') === 'true';
    
    // Apply settings
    if (darkMode) {
        document.body.classList.add('dark-mode');
    }
    
    if (highContrast) {
        document.body.classList.add('high-contrast');
    }
    
    if (reducedMotion) {
        document.body.classList.add('reduced-motion');
        document.body.classList.add('reduce-animations');
    }
    
    if (enhancedA11y) {
        document.body.classList.add('enhanced-a11y');
    }
    
    if (dyslexiaFont) {
        document.body.classList.add('dyslexia-font');
    }
    
    if (focusMode) {
        document.body.classList.add('focus-mode');
    }
    
    // Apply text size
    document.documentElement.style.setProperty('--text-size-factor', parseInt(textSize) / 100);
    document.documentElement.style.setProperty('--font-size-multiplier', parseInt(textSize) / 100);
    
    // Apply font family
    document.documentElement.style.setProperty('--font-family', fontFamily);
    
    // Apply line spacing
    document.documentElement.style.setProperty('--line-spacing', lineSpacing);
    document.documentElement.style.setProperty('--line-spacing-multiplier', parseFloat(lineSpacing));
    
    // Now fetch from server to ensure we have the latest settings
    fetch('/api/settings/accessibility/get')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const settings = data.settings;
                
                // Update localStorage with server values
                for (const [key, value] of Object.entries(settings)) {
                    localStorage.setItem(key, value.toString());
                }
                
                // Apply settings if they've changed
                if (settings.dark_mode && !darkMode) {
                    document.body.classList.add('dark-mode');
                } else if (!settings.dark_mode && darkMode) {
                    document.body.classList.remove('dark-mode');
                }
                
                if (settings.high_contrast && !highContrast) {
                    document.body.classList.add('high-contrast');
                } else if (!settings.high_contrast && highContrast) {
                    document.body.classList.remove('high-contrast');
                }
                
                const newReducedMotion = settings.reduced_motion || settings.reduce_animations;
                if (newReducedMotion && !reducedMotion) {
                    document.body.classList.add('reduced-motion');
                    document.body.classList.add('reduce-animations');
                } else if (!newReducedMotion && reducedMotion) {
                    document.body.classList.remove('reduced-motion');
                    document.body.classList.remove('reduce-animations');
                }
                
                if (settings.enhanced_a11y && !enhancedA11y) {
                    document.body.classList.add('enhanced-a11y');
                } else if (!settings.enhanced_a11y && enhancedA11y) {
                    document.body.classList.remove('enhanced-a11y');
                }
                
                if (settings.dyslexia_font && !dyslexiaFont) {
                    document.body.classList.add('dyslexia-font');
                } else if (!settings.dyslexia_font && dyslexiaFont) {
                    document.body.classList.remove('dyslexia-font');
                }
                
                if (settings.focus_mode && !focusMode) {
                    document.body.classList.add('focus-mode');
                } else if (!settings.focus_mode && focusMode) {
                    document.body.classList.remove('focus-mode');
                }
                
                // Update text size if changed
                const newTextSize = settings.font_size || settings.text_size;
                if (newTextSize && newTextSize !== parseInt(textSize)) {
                    document.documentElement.style.setProperty('--text-size-factor', newTextSize / 100);
                    document.documentElement.style.setProperty('--font-size-multiplier', newTextSize / 100);
                }
                
                // Update font family if changed
                if (settings.font_family && settings.font_family !== fontFamily) {
                    document.documentElement.style.setProperty('--font-family', settings.font_family);
                }
                
                // Update line spacing if changed
                if (settings.line_spacing && settings.line_spacing !== parseFloat(lineSpacing)) {
                    document.documentElement.style.setProperty('--line-spacing', settings.line_spacing);
                    document.documentElement.style.setProperty('--line-spacing-multiplier', settings.line_spacing / 100);
                }
            }
        })
        .catch(error => {
            console.error('Error fetching accessibility settings:', error);
        });
}

// Accessibility toggle button removed - now accessible through settings page

/**
 * Detect keyboard navigation to show focus indicators
 */
function detectKeyboardNavigation() {
    // Add class to body when using mouse
    document.body.addEventListener('mousedown', function() {
        document.body.classList.add('using-mouse');
    });
    
    // Remove class when using keyboard
    document.body.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            document.body.classList.remove('using-mouse');
        }
    });
}

/**
 * Set up keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    // Check if keyboard shortcuts are enabled
    const keyboardShortcutsEnabled = localStorage.getItem('keyboard_shortcuts') === 'true';
    window.keyboardShortcutsEnabled = keyboardShortcutsEnabled;
    
    if (!keyboardShortcutsEnabled) {
        return;
    }
    
    // Add event listener for keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Only handle Alt key combinations
        if (e.altKey) {
            switch (e.key.toLowerCase()) {
                case 'h':
                    // Go to home/dashboard
                    window.location.href = '/dashboard';
                    e.preventDefault();
                    break;
                case 'f':
                    // Go to flashcards
                    window.location.href = '/flashcards';
                    e.preventDefault();
                    break;
                case 'g':
                    // Go to grades
                    window.location.href = '/grades';
                    e.preventDefault();
                    break;
                case 't':
                    // Go to timetable
                    window.location.href = '/timetable';
                    e.preventDefault();
                    break;
                case 'd':
                    // Go to discussions
                    window.location.href = '/discussions';
                    e.preventDefault();
                    break;
                case 's':
                    // Go to settings
                    window.location.href = '/settings';
                    e.preventDefault();
                    break;
                case 'a':
                    // Go to study analytics
                    window.location.href = '/study_analytics';
                    e.preventDefault();
                    break;
                case 'x':
                    // Go to accessibility settings
                    window.location.href = '/accessibility';
                    e.preventDefault();
                    break;
            }
        } else if (e.key === '/') {
            // Focus search
            const searchInput = document.querySelector('input[type="search"]');
            if (searchInput) {
                searchInput.focus();
                e.preventDefault();
            }
        } else if (e.key === 'Escape') {
            // Close modal/popup
            const closeButton = document.querySelector('.modal.show .close, .modal.show .btn-close');
            if (closeButton) {
                closeButton.click();
                e.preventDefault();
            }
        }
    });
    
    // Add keyboard shortcuts helper
    const showHelperKey = 'F1';
    document.addEventListener('keydown', function(e) {
        if (e.key === showHelperKey) {
            toggleKeyboardShortcutsHelper();
            e.preventDefault();
        }
    });
}

/**
 * Toggle keyboard shortcuts helper
 */
function toggleKeyboardShortcutsHelper() {
    let helper = document.querySelector('.keyboard-shortcuts-helper');
    
    if (helper) {
        // Remove if already exists
        helper.remove();
        return;
    }
    
    // Create helper
    helper = document.createElement('div');
    helper.className = 'keyboard-shortcuts-helper';
    helper.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="mb-0">Keyboard Shortcuts</h6>
            <button type="button" class="btn-close btn-sm" aria-label="Close"></button>
        </div>
        <div class="shortcuts-list">
            <div class="mb-1"><kbd>Alt</kbd> + <kbd>H</kbd> - Dashboard</div>
            <div class="mb-1"><kbd>Alt</kbd> + <kbd>F</kbd> - Flashcards</div>
            <div class="mb-1"><kbd>Alt</kbd> + <kbd>G</kbd> - Grades</div>
            <div class="mb-1"><kbd>Alt</kbd> + <kbd>T</kbd> - Timetable</div>
            <div class="mb-1"><kbd>Alt</kbd> + <kbd>D</kbd> - Discussions</div>
            <div class="mb-1"><kbd>Alt</kbd> + <kbd>S</kbd> - Settings</div>
            <div class="mb-1"><kbd>Alt</kbd> + <kbd>A</kbd> - Study Analytics</div>
            <div class="mb-1"><kbd>Alt</kbd> + <kbd>X</kbd> - Accessibility Settings</div>
            <div class="mb-1"><kbd>/</kbd> - Focus Search</div>
            <div class="mb-1"><kbd>Esc</kbd> - Close Modal</div>
            <div class="mb-1"><kbd>F1</kbd> - Show/Hide This Helper</div>
        </div>
    `;
    
    // Add close button functionality
    helper.querySelector('.btn-close').addEventListener('click', function() {
        helper.remove();
    });
    
    // Add to body
    document.body.appendChild(helper);
}