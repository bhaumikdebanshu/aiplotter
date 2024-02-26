const prompts = [
    "How are you feeling today?",
    "On a scale of 1 to 10, how would you rate your mood?",
    "What emotions are you experiencing right now?",
    "Is there anything on your mind that you'd like to talk about?",
    "Do you feel happy, sad, or somewhere in between?",
    "Are there any specific events that have affected your mood recently?",
    "Would you like to share what's been bothering you?",
    "Do you find it easy to express your feelings?",
    "In what ways can I support you today?",
    "What activities usually help improve your mood?",
  ];


const randomIndex = Math.floor(Math.random() * prompts.length);
const promptElement = document.getElementById("prompt-question");
promptElement.innerHTML = prompts[randomIndex];


function pressed(e) {
  if ( (window.event ? event.keyCode : e.which) == 13) { 
      document.getElementById('modal-background-id').style.display = "block";
      document.getElementById("modal-container").style.display = "block";
      document.forms[0].submit();
      document.getElementById('answer-textarea').disabled= 'true';
  }


  
}

const heading = document.getElementById("modal-heading-text");
setInterval(function() {
  if (heading.innerHTML === "Drawing") {
    heading.innerHTML = "Analyzing";
  } else {
    heading.innerHTML = "Drawing";
  }
}, 2000);