import { useState } from 'react'

function ArticleCard({ title, excerpt }) {
  const [liked, setLiked] = useState(false)
  const [likeCount, setLikeCount] = useState(0)

  const handleToggleLike = () => {
    if (liked) {
      setLikeCount((count) => count - 1)
    } else {
      setLikeCount((count) => count + 1)
    }
    setLiked((value) => !value)
  }

  return (
    <article className="card">
      <h2>{title}</h2>
      <p>{excerpt}</p>
      <button type="button" className={`like-button ${liked ? 'liked' : ''}`} onClick={handleToggleLike}>
        {liked ? '💙 Liked' : '🤍 Like'} {likeCount}
      </button>
      <a href="#">Read More</a>
    </article>
  )
}

export default ArticleCard
