function Footer({ searchText, setSearchText }) {
  const handleSearch = () => {
    if (!searchText.trim()) {
      alert('Please enter a search term!')
      return
    }

    alert(`Searching archives for: ${searchText}`)
  }

  return (
    <footer>
      <p>© 2026 Daily News. All rights reserved.</p>
      <div className="footer-search">
        <input
          type="text"
          placeholder="Search articles..."
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
        />
        <button type="button" className="search-button" onClick={handleSearch}>
          Search
        </button>
        <p>
          Search: <i>{searchText || 'Nothing typed yet.'}</i>
        </p>
        <p className="char-count">{searchText.length}/50 characters</p>
      </div>
    </footer>
  )
}

export default Footer
