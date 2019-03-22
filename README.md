# Qobuz API

## Examples

### Client

Instantiate the client

```python
qobuz_client = qobuz.QobuzApi(app_id, app_secret, user_auth_token, format_id, cache_dir, log_dir)
```

### Favorites

Paginate through all favourite artists

```python
for artists in qobuz_client.get_favorites(qobuz.FavoriteType.ARTIST, limit=2):
    print(artists)
```