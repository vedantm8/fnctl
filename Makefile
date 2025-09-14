.PHONY: deb clean

deb:
	dpkg-buildpackage -us -uc -b

clean:
	rm -rf build dist *.egg-info
	rm -rf ../fnctl_*.deb ../fnctl_*.changes ../fnctl_*.buildinfo ../fnctl_*.tar.* ../fnctl_*

