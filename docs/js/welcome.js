// Mietspiegel Berlin — welcome overlay (ES module)

export function dismissWelcome() {
  document.getElementById('welcome').style.display = 'none';
  localStorage.setItem('mietspiegel-welcome', '1');
}

export function showWelcome() {
  document.getElementById('welcome').style.display = 'flex';
}
