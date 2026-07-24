/* ==========================================================================
   search.js — fullscreen overlay + real live search with autocomplete, keyboard navigation, and database-driven suggestions
   ========================================================================== */
(function () {
  const overlay = document.getElementById('searchOverlay');
  const trigger = document.getElementById('searchTrigger');
  const closeBtn = document.getElementById('searchClose');
  const input = document.getElementById('searchInput');
  const defaultState = document.getElementById('searchDefaultState');
  const resultsState = document.getElementById('searchResultsState');
  const resultsTarget = document.getElementById('searchResultsTarget');
  const suggestionsContainer = document.getElementById('searchSuggestions'); // We'll add this to the overlay

  if (!overlay) return;

  function openSearch() {
    overlay.classList.add('is-open');
    setTimeout(() => input.focus(), 300);
  }

  function closeSearch() {
    overlay.classList.remove('is-open');
    // Clear search when closing
    input.value = '';
    defaultState.style.display = '';
    resultsState.style.display = 'none';
    hideSuggestions();
  }

  trigger && trigger.addEventListener('click', openSearch);
  closeBtn && closeBtn.addEventListener('click', closeSearch);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSearch();
    // Handle keyboard navigation for autocomplete suggestions
    if (e.key === 'ArrowDown' && suggestionsContainer.style.display !== 'none') {
      e.preventDefault();
      focusNextSuggestion();
    }
    if (e.key === 'ArrowUp' && suggestionsContainer.style.display !== 'none') {
      e.preventDefault();
      focusPreviousSuggestion();
    }
    if (e.key === 'Enter' && suggestionsContainer.style.display !== 'none') {
      e.preventDefault();
      selectActiveSuggestion();
    }
    if (e.key === 'Escape' && suggestionsContainer.style.display !== 'none') {
      e.preventDefault();
      hideSuggestions();
    }
  });

  document.querySelectorAll('.search-chip-fill').forEach((chip) => {
    chip.addEventListener('click', () => {
      input.value = chip.textContent.trim();
      input.dispatchEvent(new Event('input'));
    });
  });

  let debounceTimer;
  let suggestions = [];
  let activeSuggestionIndex = -1;

  function showSuggestions(suggestionsArray) {
    suggestions = suggestionsArray;
    if (suggestions.length === 0) {
      hideSuggestions();
      return;
    }

    // Create suggestions container if it doesn't exist
    if (!suggestionsContainer) {
      const suggestionsDiv = document.createElement('div');
      suggestionsDiv.id = 'searchSuggestions';
      suggestionsDiv.className = 'search-suggestions';
      // Insert after input
      input.parentNode.insertBefore(suggestionsDiv, input.nextSibling);
    }

    // Clear and populate suggestions
    suggestionsContainer.innerHTML = '';
    suggestions.forEach((suggestion, index) => {
      const div = document.createElement('div');
      div.className = 'suggestion-item';
      div.textContent = suggestion;
      div.dataset.index = index;

      // Highlight matching part
      const query = input.value.trim();
      if (query) {
        const regex = new RegExp(`(${query})`, 'gi');
        const highlighted = suggestion.replace(regex, '<mark>$1</mark>');
        div.innerHTML = highlighted;
      }

      div.addEventListener('click', () => {
        selectSuggestion(suggestion);
      });

      div.addEventListener('mouseenter', () => {
        setActiveSuggestion(index);
      });

      suggestionsContainer.appendChild(div);
    });

    suggestionsContainer.style.display = 'block';
    activeSuggestionIndex = -1;
  }

  function hideSuggestions() {
    if (suggestionsContainer) {
      suggestionsContainer.style.display = 'none';
    }
    activeSuggestionIndex = -1;
  }

  function setActiveSuggestion(index) {
    if (suggestionsContainer) {
      const items = suggestionsContainer.querySelectorAll('.suggestion-item');
      items.forEach((item, i) => {
        if (i === index) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });
    }
    activeSuggestionIndex = index;
  }

  function focusNextSuggestion() {
    if (!suggestionsContainer) return;
    const items = suggestionsContainer.querySelectorAll('.suggestion-item');
    if (items.length === 0) return;

    let newIndex = activeSuggestionIndex + 1;
    if (newIndex >= items.length) newIndex = 0;
    setActiveSuggestion(newIndex);
    items[newIndex].scrollIntoView({ block: 'nearest' });
  }

  function focusPreviousSuggestion() {
    if (!suggestionsContainer) return;
    const items = suggestionsContainer.querySelectorAll('.suggestion-item');
    if (items.length === 0) return;

    let newIndex = activeSuggestionIndex - 1;
    if (newIndex < 0) newIndex = items.length - 1;
    setActiveSuggestion(newIndex);
    items[newIndex].scrollIntoView({ block: 'nearest' });
  }

  function selectActiveSuggestion() {
    if (activeSuggestionIndex >= 0 && suggestions.length > activeSuggestionIndex) {
      selectSuggestion(suggestions[activeSuggestionIndex]);
    }
  }

  function selectSuggestion(value) {
    input.value = value;
    input.dispatchEvent(new Event('input'));
    hideSuggestions();
  }

  function fetchSuggestions(query) {
    if (!query || query.length < 2) {
      hideSuggestions();
      return;
    }

    // Show loading state
    if (suggestionsContainer) {
      suggestionsContainer.innerHTML = '<div class="suggestion-item">Searching...</div>';
      suggestionsContainer.style.display = 'block';
    }

    fetch(`/search/suggestions/?q=${encodeURIComponent(query)}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json())
    .then(data => {
      if (data.suggestions && data.suggestions.length > 0) {
        showSuggestions(data.suggestions);
      } else {
        hideSuggestions();
      }
    })
    .catch(error => {
      console.error('Error fetching suggestions:', error);
      hideSuggestions();
    });
  }

  input && input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const query = input.value.trim();

    // Handle suggestions
    if (query.length >= 2) {
      debounceTimer = setTimeout(() => {
        fetchSuggestions(query);
      }, 300);
    } else {
      hideSuggestions();
    }

    // Handle main search results
    if (!query) {
      defaultState.style.display = '';
      resultsState.style.display = 'none';
      hideSuggestions();
      return;
    }

    debounceTimer = setTimeout(() => {
      fetch(`/search/?q=${encodeURIComponent(query)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then((r) => r.json())
        .then((data) => {
          defaultState.style.display = 'none';
          resultsState.style.display = '';
          resultsTarget.innerHTML = data.html;
          hideSuggestions(); // Hide suggestions when showing results
        });
    }, 280);
  });

  // Hide suggestions when clicking outside
  document.addEventListener('click', (e) => {
    if (suggestionsContainer && !suggestionsContainer.contains(e.target) && e.target !== input) {
      hideSuggestions();
    }
  });
})();
