# Maintainer: Michael Schönitzer <michael@schoenitzer.de>
pkgname=getrid
pkgver=0.2
pkgrel=1
pkgdesc="Terminal user interface to decide which packages to keep and which to get rid of"
arch=('any')
url="https://github.com/Nudin/getrid"
license=('GPL')
depends=('python' 'python-urwid' 'pacgraph')
source=('git+https://github.com/Nudin/getrid.git')
md5sums=('SKIP')

package() {
	cd "$pkgname"
	make DESTDIR="$pkgdir/" install
}
