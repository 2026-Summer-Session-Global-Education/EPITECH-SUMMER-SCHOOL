function Footer({ searchText, setSearchText }) {
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
        <p>
          Search: <i>{searchText || 'Nothing typed yet.'}</i>
        </p>
      </div>
    </footer>
  )
}

export default Footer
