function Header({ isDarkMode, setIsDarkMode }) {
  return (
    <header>
      <h1>Daily News</h1>
      <div className="header-actions">
        <nav>
          <a href="#">Politics</a>
          <a href="#">Business</a>
          <a href="#">World</a>
        </nav>
        <button
          type="button"
          className="theme-toggle"
          onClick={() => setIsDarkMode(!isDarkMode)}
        >
          {isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
        </button>
      </div>
    </header>
  )
}

export default Header
