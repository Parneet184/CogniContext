
// CogniContext frontend connected to the Japji Sahib retrieval API.
// Start FastAPI on http://127.0.0.1:8001 and serve this frontend on port 8000.

const API_BASE = 'http://127.0.0.1:8001';
const $ = (id) => document.getElementById(id);

let energy = null;
let emotion = null;
let active = 0;
let large = false;
let retrieved = [];
let currentPauri = null;
let sessionId = crypto.randomUUID();

let assessmentIndex = 0;
let assessmentAnswers = {};
let suggestedEmotion = null;

const names = [
  'Grateful',
  'At Peace',
  'Overwhelmed',
  'Heavy / Sad',
  'Frustrated',
  'Lost'
];

const slugs = {
  'Grateful': 'grateful',
  'At Peace': 'at_peace',
  'Overwhelmed': 'overwhelmed',
  'Heavy / Sad': 'heavy_sad',
  'Frustrated': 'frustrated',
  'Lost': 'lost'
};

const descriptions = [
  'Appreciating what is present',
  'Feeling steady and content',
  'Carrying too much at once',
  'Moving through a difficult moment',
  'Feeling tension or impatience',
  'Searching for clarity or direction'
];

const icons = ['✧', '○', '≋', '☾', '↝', '◇'];

const queries = {
  'Grateful': 'I feel grateful and want to deepen my appreciation',
  'At Peace': 'I feel calm and want to remain peaceful and content',
  'Overwhelmed': 'I feel overwhelmed and need steadiness and inner peace',
  'Heavy / Sad': 'I feel sad and emotionally heavy and need comfort',
  'Frustrated': 'I feel frustrated and need patience and perspective',
  'Lost': 'I feel lost and confused and need clarity and direction'
};

const assessmentQuestions = [
    {
        emotion: 'Grateful',
        question: 'How often do you feel thankful for the people, experiences, and things in your life?'
    },
    {
        emotion: 'At Peace',
        question: 'How often do you feel calm, content, and at ease with yourself?'
    },
    {
        emotion: 'Overwhelmed',
        question: 'How often do your responsibilities or thoughts feel like too much to handle?'
    },
    {
        emotion: 'Heavy / Sad',
        question: 'How often have you felt emotionally heavy, low, or sad lately?'
    },
    {
        emotion: 'Frustrated',
        question: 'How often do situations leave you feeling irritated, impatient, or frustrated?'
    },
    {
        emotion: 'Lost',
        question: 'How often do you feel uncertain about your direction or what you should do next?'
    }
];

const assessmentOptions = [
    'Never',
    'Rarely',
    'Sometimes',
    'Often',
    'Almost always'
];

function view(id) {
    [
        'energy',
        'assessment-choice',
        'assessment',
        'emotion',
        'loading',
        'notebook'
    ].forEach(key => {
        $(key).hidden = key !== id;
    });

    $('new').hidden = id !== 'notebook';
}

function renderAssessmentQuestion() {
    const question = assessmentQuestions[assessmentIndex];

    $('assessment-count').textContent =
        `QUESTION ${assessmentIndex + 1} OF 6`;

    $('assessment-percent').textContent =
        `${Math.round((assessmentIndex / 6) * 100)}% COMPLETED`;

    $('assessment-progress').style.width =
        `${((assessmentIndex + 1) / 6) * 100}%`;

    $('assessment-question').textContent = question.question;

    const container = $('assessment-options');
    container.replaceChildren();

    assessmentOptions.forEach((option, index) => {
        const button = document.createElement('button');

        button.type = 'button';
        button.className = 'answer-option';
        button.textContent = option;

        if (assessmentAnswers[assessmentIndex] === index) {
            button.classList.add('selected');
        }

        button.addEventListener('click', () => {
            assessmentAnswers[assessmentIndex] = index;

            renderAssessmentQuestion();
        });

        container.append(button);
    });

    $('assessment-back').disabled = assessmentIndex === 0;

    $('assessment-next').disabled =
        assessmentAnswers[assessmentIndex] === undefined;

    $('assessment-next').textContent =
        assessmentIndex === 5
            ? 'See my emotions →'
            : 'Next question →';
}

function startAssessment() {
    assessmentIndex = 0;
    assessmentAnswers = {};
    suggestedEmotion = null;

    renderAssessmentQuestion();
    view('assessment');
}

function finishAssessment() {
    const scores = {};

    assessmentQuestions.forEach((question, index) => {
        scores[question.emotion] = assessmentAnswers[index];
    });

    const highestScore = Math.max(...Object.values(scores));

    const leaders = Object.keys(scores).filter(
        emotion => scores[emotion] === highestScore
    );

    suggestedEmotion =
        highestScore === 0
            ? null
            : leaders[0];

    createEmotionChoices();
    view('emotion');
}


// Safely render inline bold formatting without inserting HTML.
function appendFormattedText(container, text) {
    const parts = text.split(/(\*\*.*?\*\*)/g);

    parts.forEach(part => {
        if (part.startsWith('**') && part.endsWith('**')) {
            const strong = document.createElement('strong');
            strong.textContent = part.slice(2, -2);
            container.append(strong);
        } else {
            container.append(document.createTextNode(part));
        }
    });
}

// Render paragraphs and bullet points.
function renderMessageContent(container, content) {
    const lines = content.split('\n');
    let paragraph = [];
    let list = null;

    function flushParagraph() {
        if (!paragraph.length) return;

        const p = document.createElement('p');
        appendFormattedText(p, paragraph.join(' '));
        container.append(p);
        paragraph = [];
    }

    function closeList() {
        if (list) {
            container.append(list);
            list = null;
        }
    }

    lines.forEach(line => {
        const trimmed = line.trim();

        if (!trimmed) {
            flushParagraph();
            closeList();
            return;
        }

        const bullet = trimmed.match(/^[-*]\s+(.+)/);

        if (bullet) {
            flushParagraph();

            if (!list) {
                list = document.createElement('ul');
            }

            const li = document.createElement('li');
            appendFormattedText(li, bullet[1]);
            list.append(li);
        } else {
            closeList();
            paragraph.push(trimmed);
        }
    });

    flushParagraph();
    closeList();
}

// Add a conversation message.
function addMessage(role, content) {
    const el = document.createElement('div');

    el.className =
        'message' + (role === 'YOU' ? ' user' : '');

    const title = document.createElement('div');
    title.className = 'role';
    title.textContent = role;

    const body = document.createElement('div');
    body.className = 'message-content';

    if (role === 'YOU' || role === 'SYSTEM') {
        const p = document.createElement('p');
        p.textContent = content;
        body.append(p);
    } else {
        renderMessageContent(body, content);
    }

    el.append(title, body);

    $('messages').append(el);
    $('messages').scrollTop = $('messages').scrollHeight;

    return el;
}


async function fetchPauri(number) {
  let response;
  try {
    response = await fetch(`${API_BASE}/api/v1/japji/pauris/${number}`);
  } catch (error) {
    throw new Error(
      `Cannot reach the backend while loading Pauri ${number}. Check that FastAPI is running at ${API_BASE}. ${error.message}`
    );
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `Could not load Pauri ${number} (HTTP ${response.status}): ${detail}`
    );
  }

  return response.json();
}

function renderPauri(pauri) {
  currentPauri = pauri;

  $('source-meta').textContent =
    `Japji Sahib · Pauri ${pauri.pauri_number} · Retrieval result ${active + 1} of ${retrieved.length}`;

  const gurmukhiAvailable = Boolean(
    pauri.original_gurmukhi &&
    pauri.original_gurmukhi.trim()
  );

  $('gurmukhi').textContent = gurmukhiAvailable
    ? pauri.original_gurmukhi
    : 'Verified Unicode Gurmukhi text is not available in the current imported PDF extraction.';

  $('gurmukhi').hidden = false;
  $('gurmukhi').style.fontSize = large ? '32px' : '26px';
  $('gurmukhi').style.color = gurmukhiAvailable ? '' : '#7b746c';

  $('translit').textContent =
    pauri.transliteration || 'Transliteration unavailable.';

  $('translation').textContent =
    pauri.english_translation || 'English translation unavailable.';

  $('translit-wrap').hidden = false;
  $('translation-wrap').hidden = false;

  $('toggle-trans').textContent = 'Hide transliteration';
  $('toggle-english').textContent = 'Hide translation';

  const notice = document.querySelector('.notice');

  notice.textContent =
    `Source: ${pauri.source_file || 'Japji Sahib corpus'}. Extracted text is marked ${pauri.extraction_status || 'needs review'}; translation and transliteration should be checked against a verified edition.`;

  $('sources').replaceChildren();

  retrieved.forEach((hit, index) => {
    const button = document.createElement('button');

    button.textContent =
      `Pauri ${hit.pauri_number} · similarity distance ${Number(hit.distance).toFixed(4)}${index === active ? ' · Selected' : ''}`;

    button.onclick = async () => {
      active = index;

      try {
        $('source-meta').textContent =
          `Loading Pauri ${hit.pauri_number}...`;

        const detail = await fetchPauri(hit.pauri_number);
        renderPauri(detail);

      } catch (error) {
        $('source-meta').textContent = error.message;
      }
    };

    $('sources').append(button);
  });
}

async function searchPauris() {
  const query = queries[emotion] ||
    'I want to reflect on Japji Sahib and find guidance for my present moment';

  const payload = { query, limit: 5 };
  if (emotion) payload.emotion = slugs[emotion];

  let response;
  try {
    response = await fetch(`${API_BASE}/api/v1/japji/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (error) {
    throw new Error(
      `Cannot reach the backend at ${API_BASE}. Make sure FastAPI is running on port 8001. Browser detail: ${error.message}`
    );
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `Search failed (HTTP ${response.status}): ${detail}`
    );
  }

  const data = await response.json();

  // Extract results from the API response.
  const results = Array.isArray(data)
    ? data
    : data.results || data.matches || data.items || [];

  if (!Array.isArray(results) || results.length === 0) {
    throw new Error(
      'No Pauris were returned. Try another emotion or remove the emotion filter.'
    );
  }

  // Validate the returned Pauri numbers.
  const validResults = results.filter(
    (item) => Number.isInteger(Number(item.pauri_number))
  );

  if (!validResults.length) {
    throw new Error(
      'The API returned results without valid Pauri numbers. Please check the backend response format.'
    );
  }

  retrieved = validResults;
  active = 0;

  const first = await fetchPauri(retrieved[0].pauri_number);

  return { data, first };
}


// ------------------------------------------
// GROQ CHAT API
// ------------------------------------------

async function sendChatRequest(message) {

    const payload = {
        session_id: sessionId,
        message: message,
        emotional_state: emotion ? slugs[emotion] : null,
        energy_level: energy,
        active_source_ids: [],
        limit: 5
    };

    let response;

    try {
        response = await fetch(`${API_BASE}/api/v1/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

    } catch (error) {
        throw new Error(
            `Cannot connect to the chat API: ${error.message}`
        );
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.detail || `Chat request failed: HTTP ${response.status}`
        );
    }

    if (!data.answer) {
        throw new Error('The chat API returned an empty answer.');
    }

    return data;
}



async function beginReflection() {
    view('loading');

    $('status').textContent =
        'Finding a reflection for your present moment...';

    $('context').textContent =
        `${energy || 'Energy not selected'} · ${emotion || 'No emotion selected'}`;

    $('messages').replaceChildren();
    $('suggestions').replaceChildren();
    $('sources').replaceChildren();

    try {
        // 1. Prepare the initial question for the selected emotion
        const query = queries[emotion] ||
            'I want to reflect on Japji Sahib and find guidance for my present moment';

        // 2. Send the request to FastAPI -> ChromaDB -> Groq
        const chatData = await sendChatRequest(query);

        // 3. Store the retrieved scripture passages
        retrieved = chatData.sources || [];
        active = 0;

        if (retrieved.length === 0) {
            throw new Error('No relevant Japji Sahib passages were found.');
        }

        // 4. Load the first retrieved Pauri
        const first = await fetchPauri(
            retrieved[0].pauri_number
        );

        renderPauri(first);

        // 5. Display the AI-generated reflection
        addMessage(
            'COGNICONTEXT · GROQ',
            chatData.answer
        );

        // 6. Display suggested questions
        addSuggestions();

        // 7. Open the reflection workspace
        view('notebook');

    } catch (error) {
        console.error('Reflection error:', error);

        view('emotion');

        alert(
            `Unable to generate your reflection.\n\n${error.message}`
        );
    }
}


// ------------------------------------------
// SUGGESTED QUESTIONS
// ------------------------------------------

function addSuggestions() {
  const suggestions = [
    'Explain this passage simply',
    'Why might this passage be relevant?',
    'Show me another related Pauri'
  ];

  $('suggestions').replaceChildren();

  suggestions.forEach((text) => {
    const button = document.createElement('button');

    button.textContent = text;

    button.onclick = () => {
      if (text.includes('another')) {
        nextPauri();
      } else {
        $('message').value = text;
        $('composer').requestSubmit();
      }
    };

    $('suggestions').append(button);
  });
}

// ------------------------------------------
// NAVIGATE THROUGH RETRIEVED PAURIS
// ------------------------------------------

async function nextPauri() {
  if (active + 1 >= retrieved.length) {
    addMessage(
      'SYSTEM',
      'You have reached the end of the retrieved results.'
    );
    return;
  }

  active++;

  try {
    const number = retrieved[active].pauri_number;

    $('source-meta').textContent =
      `Loading Pauri ${number}...`;

    const detail = await fetchPauri(number);

    renderPauri(detail);

    addMessage(
      'SYSTEM',
      `Now showing retrieved Pauri ${number}.`
    );

  } catch (error) {
    console.error(error);
    addMessage('SYSTEM', error.message);
  }
}

// ------------------------------------------
// CHAT COMPOSER — RETRIEVAL-ONLY MODE
// ------------------------------------------


async function sendUserMessage(event) {
    event.preventDefault();

    const text = $('message').value.trim();

    if (!text) return;

    // Display the user's message
    addMessage('YOU', text);

    $('message').value = '';

    // Display a temporary loading message
    addMessage('COGNICONTEXT', 'Reflecting on your question...');

    const loadingMessage = $('messages').lastElementChild;

    try {
        // Send the message to FastAPI and Groq
        const chatData = await sendChatRequest(text);

        // Remove the loading message
        loadingMessage.remove();

        // Update retrieved scripture sources
        if (Array.isArray(chatData.sources) && chatData.sources.length > 0) {
            retrieved = chatData.sources;
            active = 0;

            const first = await fetchPauri(
                retrieved[0].pauri_number
            );

            renderPauri(first);
        }

        // Display Groq's response
        addMessage(
            'COGNICONTEXT · GROQ',
            chatData.answer
        );

    } catch (error) {
        console.error('Chat error:', error);

        loadingMessage.remove();

        addMessage(
            'SYSTEM',
            `Unable to generate a response: ${error.message}`
        );
    }
}


// ------------------------------------------
// ASSESSMENT: EMOTION CHOICES
// ------------------------------------------

function createEmotionChoices() {
    const container = $('emotions');
    container.replaceChildren();

    const resultBox = $('assessment-result');

    if (suggestedEmotion) {
        resultBox.hidden = false;

        $('suggested-emotion-title').textContent =
            `You may be feeling ${suggestedEmotion}.`;

        $('suggested-emotion-message').textContent =
            `Based on your responses, ${suggestedEmotion.toLowerCase()} seems to reflect your present emotional state.`;

    } else {
        resultBox.hidden = true;
    }

    names.forEach((name, index) => {
        const button = document.createElement('button');

        button.className = 'choice';
        button.type = 'button';

        button.innerHTML = `
            <span class="symbol">${icons[index]}</span>
            <strong>${name}</strong>
            <span>${descriptions[index]}</span>
        `;

        if (name === suggestedEmotion) {
            button.classList.add('suggested');
        }

        button.addEventListener('click', () => {
            emotion = name;

            container.querySelectorAll('.choice').forEach(choice => {
                choice.classList.remove('selected');
            });

            button.classList.add('selected');
            $('find').disabled = false;
        });

        container.append(button);
    });

    // Reset selection whenever the emotion screen is opened
    emotion = null;
    $('find').disabled = true;
}

// ------------------------------------------
// ENERGY SELECTION
// ------------------------------------------

// ENERGY -> ASSESSMENT CHOICE

document.querySelectorAll('[data-energy]').forEach(button => {
    button.addEventListener('click', () => {
        energy = button.dataset.energy;

        document.querySelectorAll('[data-energy]').forEach(choice => {
            choice.classList.remove('selected');
        });

        button.classList.add('selected');

        view('assessment-choice');
    });
});

// ASSESSMENT PATH

$('take-assessment').addEventListener('click', startAssessment);

$('skip-assessment').addEventListener('click', () => {
    suggestedEmotion = null;
    createEmotionChoices();
    view('emotion');
});

$('back-energy').addEventListener('click', () => {
    view('energy');
});

// ASSESSMENT NAVIGATION

$('assessment-back').addEventListener('click', () => {
    if (assessmentIndex > 0) {
        assessmentIndex--;
        renderAssessmentQuestion();
    }
});

$('assessment-next').addEventListener('click', () => {
    if (assessmentAnswers[assessmentIndex] === undefined) return;

    if (assessmentIndex < 5) {
        assessmentIndex++;
        renderAssessmentQuestion();
    } else {
        finishAssessment();
    }
});

$('assessment-exit').addEventListener('click', () => {
    suggestedEmotion = null;
    createEmotionChoices();
    view('emotion');
});

// ------------------------------------------
// NAVIGATION
// ------------------------------------------

$('back').addEventListener('click', () => {
  view('assessment-choice');
});


$('find').addEventListener('click', () => {
  if (!emotion) return;
  beginReflection();
});

$('new').addEventListener('click', () => {
  sessionId = crypto.randomUUID();
  energy = null;
  emotion = null;
  retrieved = [];
  active = 0;
  currentPauri = null;
  assessmentIndex = 0;
assessmentAnswers = {};
suggestedEmotion = null;

  $('find').disabled = true;

  document.querySelectorAll('[data-energy]').forEach((button) => {
    button.classList.remove('selected');
  });

  $('emotions').querySelectorAll('.choice').forEach((button) => {
    button.classList.remove('selected');
  });

  $('messages').replaceChildren();
  $('suggestions').replaceChildren();
  $('sources').replaceChildren();

  view('energy');
});

// ------------------------------------------
// SOURCE READER CONTROLS
// ------------------------------------------

$('toggle-trans').addEventListener('click', () => {
  const hidden = $('translit-wrap').hidden;
  $('translit-wrap').hidden = !hidden;

  $('toggle-trans').textContent = hidden
    ? 'Hide transliteration'
    : 'Show transliteration';
});

$('toggle-english').addEventListener('click', () => {
  const hidden = $('translation-wrap').hidden;
  $('translation-wrap').hidden = !hidden;

  $('toggle-english').textContent = hidden
    ? 'Hide translation'
    : 'Show translation';
});

$('copy-source').addEventListener('click', async () => {
  if (!currentPauri) return;

  const content = [
    `Japji Sahib - Pauri ${currentPauri.pauri_number}`,
    '',
    currentPauri.original_gurmukhi || '',
    '',
    currentPauri.transliteration || '',
    '',
    currentPauri.english_translation || ''
  ].join('\n');

  try {
    await navigator.clipboard.writeText(content);
    $('copy-source').textContent = 'Copied!';
  } catch (error) {
    alert('Unable to copy. Please select and copy the text manually.');
  }
});

$('size').addEventListener('click', () => {
  large = !large;

  $('gurmukhi').style.fontSize = large
    ? '32px'
    : '26px';

  $('size').textContent = large
    ? 'A− Text'
    : 'A+ Text';
});

// ------------------------------------------
// CONVERSATION COMPOSER
// ------------------------------------------

$('composer').addEventListener('submit', sendUserMessage);

// ------------------------------------------
// SYSTEM ARCHITECTURE DRAWER
// ------------------------------------------

let previousFocus = null;

$('architecture').addEventListener('click', () => {
  previousFocus = document.activeElement;
  $('overlay').hidden = false;
  $('close').focus();
});

function closeArchitecture() {
  $('overlay').hidden = true;

  if (previousFocus) {
    previousFocus.focus();
  }
}

$('close').addEventListener('click', closeArchitecture);

$('overlay').addEventListener('click', (event) => {
  if (event.target === $('overlay')) {
    closeArchitecture();
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !$('overlay').hidden) {
    closeArchitecture();
  }

  // Basic keyboard focus management for the drawer.
  if (event.key === 'Tab' && !$('overlay').hidden) {
    const focusable = [
      ...$('overlay').querySelectorAll(
        'button:not([disabled]), a[href], input, textarea'
      )
    ];

    if (!focusable.length) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (
      !event.shiftKey &&
      document.activeElement === last
    ) {
      event.preventDefault();
      first.focus();
    }
  }
});

// ------------------------------------------
// INITIALIZE APPLICATION
// ------------------------------------------

createEmotionChoices();
view('energy');

console.log('CogniContext frontend initialized.');
console.log('Backend API:', API_BASE);