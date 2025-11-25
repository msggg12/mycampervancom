Place your images in this folder:

simple-site/static/images/

Then reference them in config.json (imageUrl or photos arrays) like:

"imageUrl": "/static/images/red-van-1.jpg"
"photos": [
	"/static/images/red-van-2.jpg",
	"/static/images/red-van-3.jpg"
]

You can also use these in HTML pages:
<img src="/static/images/your-photo.jpg" alt="..." />
