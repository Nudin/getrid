install:
	mkdir -p $(DESTDIR)/opt/getrid
	ln -s /usr/bin/pacgraph $(DESTDIR)/opt/getrid/pacgraph.py
	install getrid.py $(DESTDIR)/opt/getrid/
	mkdir -p $(DESTDIR)/usr/bin
	ln -s /opt/getrid/getrid.py $(DESTDIR)/usr/bin/getrid

uninstall:
	test -f $(DESTDIR)/opt/getrid/getrid.py && rm /opt/getrid/getrid.py
	test -L $(DESTDIR)/opt/getrid/pacgraph.py && rm /opt/getrid/pacgraph.py
	test -d $(DESTDIR)/opt/getrid/ && rmdir /opt/getrid/
	test -L $(DESTDIR)/usr/bin/getrid && rm /usr/bin/getrid

update: uninstall install
