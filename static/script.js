document.addEventListener('DOMContentLoaded', (event) => {

    // --- Loading Indicator Logic ---
    const forms = document.querySelectorAll('form.feature-form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            // Find the loading indicator specific to this form/page section
            const container = this.closest('.feature-page'); // Find the parent feature page container
            if (!container) return; // Defensive check

            const loadingIndicator = container.querySelector('.loading-indicator');
            const submitButton = this.querySelector('button[type="submit"]');

            if (loadingIndicator) {
                const timerSpan = loadingIndicator.querySelector('.timer-span');
                let seconds = 0;
                loadingIndicator.classList.add('visible');

                if (timerSpan) {
                    timerSpan.textContent = '0s';
                    // Store interval ID if needed, though page reload usually handles it
                    const intervalId = setInterval(() => {
                        seconds++;
                        timerSpan.textContent = `${seconds}s`;
                    }, 1000);
                    // loadingIndicator.dataset.intervalId = intervalId; // Optional storage
                }
            }
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Generating...'; // Or more specific based on form
            }
        });
    });

    // --- Copy Button Logic (applies on pages with results) ---
    const copyButton = document.getElementById('copy-button');
    const responseTextElement = document.getElementById('response-text');
    if (copyButton && responseTextElement) {
        copyButton.addEventListener('click', () => {
            const textToCopy = responseTextElement.innerText || responseTextElement.textContent;
            navigator.clipboard.writeText(textToCopy).then(() => {
                copyButton.textContent = 'Copied!';
                copyButton.style.backgroundColor = '#28a745'; // Green
                setTimeout(() => {
                    copyButton.textContent = 'Copy Text';
                    copyButton.style.backgroundColor = '';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                copyButton.textContent = 'Copy Failed';
                copyButton.style.backgroundColor = '#dc3545'; // Red
                setTimeout(() => {
                    copyButton.textContent = 'Copy Text';
                    copyButton.style.backgroundColor = '';
                }, 3000);
            });
        });
    }

    // --- Feature Filtering Logic (for index.html) ---
    const searchInput = document.getElementById('feature-search-input');
    const featureGrid = document.querySelector('.feature-grid'); // Target the grid container
    const noResultsMessage = document.getElementById('no-results-message');

    if (searchInput && featureGrid && noResultsMessage) {
        const featureCards = featureGrid.querySelectorAll('.feature-card'); // Get cards inside grid

        searchInput.addEventListener('input', () => {
            const searchTerm = searchInput.value.toLowerCase().trim();
            let visibleCount = 0;

            featureCards.forEach(card => {
                const title = card.querySelector('h3')?.textContent?.toLowerCase() || '';
                const description = card.querySelector('p')?.textContent?.toLowerCase() || '';
                const cardText = title + ' ' + description;
                const isVisible = cardText.includes(searchTerm);

                // Adjust display based on grid layout (might be block, grid, flex etc.)
                // Setting to '' reverts to CSS default, 'none' hides
                card.style.display = isVisible ? '' : 'none';

                if (isVisible) {
                    visibleCount++;
                }
            });

            // Show/hide 'No results' message
            noResultsMessage.style.display = (visibleCount === 0 && searchTerm !== '') ? 'block' : 'none';
        });
    }

    // --- Prompt Library Logic (expects 'promptData' to be globally defined on feature pages) ---
    const categorySelect = document.getElementById('prompt-category-select');
    const promptSelect = document.getElementById('prompt-select');
    
    

    // Check for possible textarea IDs based on different feature pages
    const possibleTextAreaIds = ['prompt_text', 'prompt_image', 'prompt_video', 'prompt_audio', 'prompt_pdf', 'prompt_excel', 'prompt_excel_row'];
    let targetTextArea = null;
    
    // Find the first available textarea on the current page
    for (const id of possibleTextAreaIds) {
        const textArea = document.getElementById(id);
        if (textArea) {
            targetTextArea = textArea;
            break;
        }
    }

    // Define promptData if it doesn't exist to prevent errors
    const promptData = (typeof window.promptData !== 'undefined') ? window.promptData : {};

    // Check if elements exist
    if (categorySelect && promptSelect && targetTextArea && Object.keys(promptData).length > 0) {
        console.log("Setting up Prompt Library..."); // Debug log

        if (!categorySelect.dataset.populated) {
            categorySelect.dataset.populated = true; // Mark as populated
            // Populate dropdown logic here
        }

        // Populate Category Dropdown
        categorySelect.innerHTML = ''; // Clear existing options
        Object.keys(promptData).sort().forEach(category => {
            const option = document.createElement('option');
            // option.value = category;
            option.textContent = category;
            categorySelect.appendChild(option);
        });

        // Event Listener for Category Change
        categorySelect.addEventListener('change', () => {
            const selectedCategory = categorySelect.value;
            // Clear previous prompt options and reset state
           
            promptSelect.innerHTML = '<option value="">-- Select Prompt Title --</option>';
            // promptSelect.disabled = true;

            if (selectedCategory && promptData[selectedCategory]) {
                promptSelect.disabled = false; // Enable prompt select
                // Populate Prompt Dropdown with TITLES
                promptData[selectedCategory].forEach(promptItem => {
                    const option = document.createElement('option');
                    option.value = promptItem.title; // Use title as the value
                    option.textContent = promptItem.title; // Display the title
                    promptSelect.appendChild(option);
                });
            }
        });

        // Event Listener for Prompt Selection
        promptSelect.addEventListener('change', () => {
            const selectedPromptTitle = promptSelect.value;

            
            if (selectedPromptTitle) {
                // Find the full prompt text associated with the selected title
                const selectedCategory = categorySelect.value; // Get current category
                const promptObj = promptData[selectedCategory]?.find(p => p.title === selectedPromptTitle);

                if (promptObj) {
                    // Paste the ACTUAL PROMPT TEXT into the text area
                    targetTextArea.value = promptObj.prompt_text; // Use the full prompt text
                    targetTextArea.focus();
                    console.log("Pasted prompt text for:", selectedPromptTitle); // Debug log
                } else {
                     // Fallback: If somehow not found, paste the title (as per original request)
                    targetTextArea.value = selectedPromptTitle;
                    console.warn("Could not find full prompt text, pasting title:", selectedPromptTitle);
                }

                // Optional: Reset dropdowns after selection?
                // categorySelect.value = "";
                // promptSelect.innerHTML = '<option value="">-- Select Prompt Title --</option>';
                // promptSelect.disabled = true;
            }
        });

    } else {
        // If these elements aren't on the current page, this is normal.
        // console.log("Prompt library elements/data not found on this page.");
    }
    // --- End Prompt Library Logic ---

}); // End DOMContentLoaded