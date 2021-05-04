#
# Fedora spec file for redis
#
# License: MIT
# http://opensource.org/licenses/MIT
#
# Please preserve changelog entries
#

# Tests fail in mock, not in local build.
%bcond_with    tests

# Commit IDs for the (unversioned) redis-doc repository
# https://fedoraproject.org/wiki/Packaging:SourceURL "Commit Revision"
%global doc_commit 6fca484937fe6d97e2065769a90d16b4caf9dc32
%global short_doc_commit %(c=%{doc_commit}; echo ${c:0:7})

# %%{rpmmacrodir} not usable on EL-6
%global macrosdir %(d=%{_rpmconfigdir}/macros.d; [ -d $d ] || d=%{_sysconfdir}/rpm; echo $d)

Name:              redis
Version:           6.2.3
Release:           1%{?dist}
Summary:           A persistent key-value database
# redis, jemalloc, linenoise, lzf, hiredis are BSD
# lua is MIT
License:           BSD and MIT
URL:               https://redis.io
Source0:           https://download.redis.io/releases/%{name}-%{version}.tar.gz
Source1:           %{name}.logrotate
Source2:           %{name}-sentinel.service
Source3:           %{name}.service
Source6:           %{name}-shutdown
Source7:           %{name}-limit-systemd
Source9:           macros.%{name}
Source10:          https://github.com/%{name}/%{name}-doc/archive/%{doc_commit}/%{name}-doc-%{short_doc_commit}.tar.gz

# To refresh patches:
# tar xf redis-xxx.tar.gz && cd redis-xxx && git init && git add . && git commit -m "%%{version} baseline"
# git am %%{patches}
# Then refresh your patches
# git format-patch HEAD~<number of expected patches>
# Update configuration for Fedora
# https://github.com/redis/redis/pull/3491 - man pages
Patch0001:         0001-1st-man-pageis-for-redis-cli-redis-benchmark-redis-c.patch

BuildRequires: make
BuildRequires:     gcc
%if %{with tests}
BuildRequires:     procps-ng
BuildRequires:     tcl
%endif
BuildRequires:     pkgconfig(libsystemd)
BuildRequires:     systemd-devel
BuildRequires:     openssl-devel
# redis-trib functionality migrated to redis-cli
Obsoletes:         redis-trib < 5
# Required for redis-shutdown
Requires:          /bin/awk
Requires:          logrotate
Requires(pre):     shadow-utils
Requires(post):    systemd
Requires(preun):   systemd
Requires(postun):  systemd
# from deps/hiredis/hiredis.h
Provides:          bundled(hiredis) = 0.14.0
# from deps/jemalloc/VERSION
Provides:          bundled(jemalloc) = 5.1.0
# from deps/lua/src/lua.h
Provides:          bundled(lua-libs) = 5.1.5
# from deps/linenoise/linenoise.h
Provides:          bundled(linenoise) = 1.0
Provides:          bundled(lzf)

%global redis_modules_abi 1
%global redis_modules_dir %{_libdir}/%{name}/modules
Provides:          redis(modules_abi)%{?_isa} = %{redis_modules_abi}

%description
Redis is an advanced key-value store. It is often referred to as a data 
structure server since keys can contain strings, hashes, lists, sets and 
sorted sets.

You can run atomic operations on these types, like appending to a string;
incrementing the value in a hash; pushing to a list; computing set 
intersection, union and difference; or getting the member with highest 
ranking in a sorted set.

In order to achieve its outstanding performance, Redis works with an 
in-memory dataset. Depending on your use case, you can persist it either 
by dumping the dataset to disk every once in a while, or by appending 
each command to a log.

Redis also supports trivial-to-setup master-slave replication, with very 
fast non-blocking first synchronization, auto-reconnection on net split 
and so forth.

Other features include Transactions, Pub/Sub, Lua scripting, Keys with a 
limited time-to-live, and configuration settings to make Redis behave like 
a cache.

You can use Redis from most programming languages also.

%package           devel
Summary:           Development header for Redis module development
# Header-Only Library (https://fedoraproject.org/wiki/Packaging:Guidelines)
Provides:          %{name}-static = %{version}-%{release}

%description       devel
Header file required for building loadable Redis modules. Detailed
API documentation is available in the redis-doc package.

%package           doc
Summary:           Documentation for Redis including man pages
License:           CC-BY-SA
BuildArch:         noarch

# http://fedoraproject.org/wiki/Packaging:Conflicts "Splitting Packages"
Conflicts:         redis < 4.0

%description       doc
Manual pages and detailed documentation for many aspects of Redis use,
administration and development.


%prep
%setup -q -b 10
%setup -q
mv ../%{name}-doc-%{doc_commit} doc
%patch0001 -p1

mv deps/lua/COPYRIGHT    COPYRIGHT-lua
mv deps/jemalloc/COPYING COPYING-jemalloc
mv deps/hiredis/COPYING  COPYING-hiredis

# Configuration file changes
sed -i -e 's|^logfile .*$|logfile /var/log/redis/redis.log|g' redis.conf
sed -i -e 's|^logfile .*$|logfile /var/log/redis/sentinel.log|g' sentinel.conf
sed -i -e 's|^dir .*$|dir /var/lib/redis|g' redis.conf

# Module API version safety check
api=`sed -n -e 's/#define REDISMODULE_APIVER_[0-9][0-9]* //p' src/redismodule.h`
if test "$api" != "%{redis_modules_abi}"; then
   : Error: Upstream API version is now ${api}, expecting %%{redis_modules_abi}.
   : Update the redis_modules_abi macro, the rpmmacros file, and rebuild.
   exit 1
fi

%global make_flags	DEBUG="" V="echo" LDFLAGS="%{?__global_ldflags}" CFLAGS+="%{optflags} -fPIC" INSTALL="install -p" PREFIX=%{buildroot}%{_prefix} BUILD_WITH_SYSTEMD=yes BUILD_TLS=yes

%build
%make_build %{make_flags} all

%install
make %{make_flags} install

# Filesystem.
install -d %{buildroot}%{_sharedstatedir}/%{name}
install -d %{buildroot}%{_localstatedir}/log/%{name}
install -d %{buildroot}%{_localstatedir}/run/%{name}
install -d %{buildroot}%{redis_modules_dir}

# Install logrotate file.
install -pDm644 %{S:1} %{buildroot}%{_sysconfdir}/logrotate.d/%{name}

# Install configuration files.
install -pDm640 %{name}.conf  %{buildroot}%{_sysconfdir}/%{name}/%{name}.conf
install -pDm640 sentinel.conf %{buildroot}%{_sysconfdir}/%{name}/sentinel.conf

# Install systemd unit files.
mkdir -p %{buildroot}%{_unitdir}
install -pm644 %{S:3} %{buildroot}%{_unitdir}
install -pm644 %{S:2} %{buildroot}%{_unitdir}

# Install systemd limit files (requires systemd >= 204)
install -p -D -m 644 %{S:7} %{buildroot}%{_sysconfdir}/systemd/system/%{name}.service.d/limit.conf
install -p -D -m 644 %{S:7} %{buildroot}%{_sysconfdir}/systemd/system/%{name}-sentinel.service.d/limit.conf

# Fix non-standard-executable-perm error.
chmod 755 %{buildroot}%{_bindir}/%{name}-*

# Install redis-shutdown
install -pDm755 %{S:6} %{buildroot}%{_libexecdir}/%{name}-shutdown

# Install redis module header
install -pDm644 src/%{name}module.h %{buildroot}%{_includedir}/%{name}module.h

# Install man pages
man=$(dirname %{buildroot}%{_mandir})
for page in man/man?/*; do
    install -Dpm644 $page $man/$page
done
ln -s redis-server.1 %{buildroot}%{_mandir}/man1/redis-sentinel.1
ln -s redis.conf.5   %{buildroot}%{_mandir}/man5/redis-sentinel.conf.5

# Install documentation and html pages
doc=$(echo %{buildroot}/%{_docdir}/%{name})
for page in 00-RELEASENOTES BUGS CONTRIBUTING MANIFESTO; do
    install -Dpm644 $page $doc/$page
done
for page in $(find doc -name \*.md | sed -e 's|.md$||g'); do
    base=$(echo $page | sed -e 's|doc/||g')
    install -Dpm644 $page.md $doc/$base.md
done

# Install rpm macros for redis modules
mkdir -p %{buildroot}%{macrosdir}
install -pDm644 %{S:9} %{buildroot}%{macrosdir}/macros.%{name}

%check
%if %{with tests}
# https://github.com/redis/redis/issues/1417 (for "taskset -c 1")
taskset -c 1 make %{make_flags} test
make %{make_flags} test-sentinel
%endif

%pre
getent group %{name} &> /dev/null || \
groupadd -r %{name} &> /dev/null
getent passwd %{name} &> /dev/null || \
useradd -r -g %{name} -d %{_sharedstatedir}/%{name} -s /sbin/nologin \
-c 'Redis Database Server' %{name} &> /dev/null
exit 0

%post
if [ -f %{_sysconfdir}/%{name}.conf -a ! -L %{_sysconfdir}/%{name}.conf ]; then
  if [ -f %{_sysconfdir}/%{name}/%{name}.conf.rpmnew ]; then
    rm    %{_sysconfdir}/%{name}/%{name}.conf.rpmnew
  fi
  if [ -f %{_sysconfdir}/%{name}/%{name}.conf ]; then
    mv    %{_sysconfdir}/%{name}/%{name}.conf %{_sysconfdir}/%{name}/%{name}.conf.rpmnew
  fi
  mv %{_sysconfdir}/%{name}.conf %{_sysconfdir}/%{name}/%{name}.conf
  echo -e "\nWarning: %{name} configuration is now in %{_sysconfdir}/%{name} directory\n"
fi
if [ -f %{_sysconfdir}/%{name}-sentinel.conf  -a ! -L %{_sysconfdir}/%{name}-sentinel.conf  ]; then
  if [ -f %{_sysconfdir}/%{name}/sentinel.conf.rpmnew ]; then
    rm    %{_sysconfdir}/%{name}/sentinel.conf.rpmnew
  fi
  if [ -f %{_sysconfdir}/%{name}/sentinel.conf ]; then
    mv    %{_sysconfdir}/%{name}/sentinel.conf %{_sysconfdir}/%{name}/sentinel.conf.rpmnew
  fi
  mv %{_sysconfdir}/%{name}-sentinel.conf %{_sysconfdir}/%{name}/sentinel.conf
fi
%systemd_post %{name}.service
%systemd_post %{name}-sentinel.service

%preun
%systemd_preun %{name}.service
%systemd_preun %{name}-sentinel.service

%postun
%systemd_postun_with_restart %{name}.service
%systemd_postun_with_restart %{name}-sentinel.service

%files
%{!?_licensedir:%global license %%doc}
%license COPYING
%license COPYRIGHT-lua
%license COPYING-jemalloc
%license COPYING-hiredis
%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}
%attr(0750, redis, root) %dir %{_sysconfdir}/%{name}
%attr(0640, redis, root) %config(noreplace) %{_sysconfdir}/%{name}/%{name}.conf
%attr(0640, redis, root) %config(noreplace) %{_sysconfdir}/%{name}/sentinel.conf
%dir %attr(0750, redis, redis) %{_libdir}/%{name}
%dir %attr(0750, redis, redis) %{redis_modules_dir}
%dir %attr(0750, redis, redis) %{_sharedstatedir}/%{name}
%dir %attr(0750, redis, redis) %{_localstatedir}/log/%{name}
%exclude %{macrosdir}
%exclude %{_includedir}
%exclude %{_docdir}/%{name}/*
%{_bindir}/%{name}-*
%{_libexecdir}/%{name}-*
%{_mandir}/man1/%{name}*
%{_mandir}/man5/%{name}*
%{_unitdir}/%{name}.service
%{_unitdir}/%{name}-sentinel.service
%dir %{_sysconfdir}/systemd/system/%{name}.service.d
%config(noreplace) %{_sysconfdir}/systemd/system/%{name}.service.d/limit.conf
%dir %{_sysconfdir}/systemd/system/%{name}-sentinel.service.d
%config(noreplace) %{_sysconfdir}/systemd/system/%{name}-sentinel.service.d/limit.conf
%dir %attr(0755, redis, redis) %ghost %{_localstatedir}/run/%{name}

%files devel
# main package is not required
%license COPYING
%{_includedir}/%{name}module.h
%{macrosdir}/*

%files doc
# main package is not required
%license COPYING
%docdir %{_docdir}/%{name}
%{_docdir}/%{name}


%changelog
* Tue May  4 2021 Remi Collet <remi@remirepo.net> - 6.2.3-1
- Upstream 6.2.3 release

* Tue Apr 20 2021 Remi Collet <remi@remirepo.net> - 6.2.2-1
- Upstream 6.2.2 release

* Thu Apr 01 2021 Nathan Scott <nathans@redhat.com> - 6.2.1-1
- Upstream 6.2.1 release
- Merged make-macros spec change from Tom Stellard

* Tue Mar 02 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 6.2.0-2
- Rebuilt for updated systemd-rpm-macros
  See https://pagure.io/fesco/issue/2583.

* Mon Mar 01 2021 Nathan Scott <nathans@redhat.com> - 6.2.0-1
- Upstream 6.2.0 release (RHBZ #1915463).
- drop patch merged upstream.

* Wed Feb 24 2021 Nathan Scott <nathans@redhat.com> - 6.0.11-1
- Upstream 6.0.11 release.

* Wed Jan 27 2021 Fedora Release Engineering <releng@fedoraproject.org> - 6.0.10-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_34_Mass_Rebuild

* Wed Jan 13 2021 Remi Collet <remi@remirepo.net> - 6.0.10-1
- Upstream 6.0.10 release.

* Tue Nov 24 2020 Remi Collet <remi@remirepo.net> - 6.0.9-3
- fix check for regular file, not symlink

* Mon Nov 23 2020 Remi Collet <remi@remirepo.net> - 6.0.9-2
- move configuration in /etc/redis per upstream recommendation
  see https://github.com/redis/redis/issues/8051

* Tue Oct 27 2020 Remi Collet <remi@remirepo.net> - 6.0.9-1
- Upstream 6.0.9 release.

* Tue Oct 20 2020 Remi Collet <remi@remirepo.net> - 6.0.8-2
- add missing LICENSE files in main package

* Thu Sep 10 2020 Remi Collet <remi@remirepo.net> - 6.0.8-1
- Upstream 6.0.8 release.

* Tue Sep  1 2020 Remi Collet <remi@remirepo.net> - 6.0.7-1
- Upstream 6.0.7 release.
- drop patch merged upstream

* Wed Jul 29 2020 Fedora Release Engineering <releng@fedoraproject.org> - 6.0.6-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Tue Jul 21 2020 Remi Collet <rcollet@redhat.com> - 6.0.6-1
- Upstream 6.0.6 release.
- drop patch merged upstream
- open https://github.com/redis/redis/pull/7543 fix deprecated tail syntax

* Wed Jun 10 2020 Nathan Scott <nathans@redhat.com> - 6.0.5-1
- Upstream 6.0.5 release.

* Thu May 28 2020 Remi Collet <remi@remirepo.net> - 6.0.4-3
- Add comment for TimeoutStartSec and TimeoutStopSec in limit.conf
- Fix missing notification to systemd for sentinel
  patch from https://github.com/redis/redis/pull/7168
- Upstream 6.0.4 release.

* Mon May 18 2020 Nathan Scott <nathans@redhat.com> - 6.0.3-1
- Upstream 6.0.3 release.

* Wed May  6 2020 Remi Collet <rcollet@redhat.com> - 6.0.1-1
- Upstream 6.0.1 release.

* Fri May 01 2020 Nathan Scott <nathans@redhat.com> - 6.0.0-1
- Upstream 6.0.0 release.

* Fri Mar 13 2020 Nathan Scott <nathans@redhat.com> - 5.0.8-1
- Upstream 5.0.8 release.

* Wed Feb 12 2020 Nathan Scott <nathans@redhat.com> - 5.0.7-3
- Patch extern SDS_NOINIT definition for gcc 10 (RHBZ #1799969)

* Thu Jan 30 2020 Fedora Release Engineering <releng@fedoraproject.org> - 5.0.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_32_Mass_Rebuild

* Tue Nov 19 2019 Carl George <carl@george.computer> - 5.0.7-1
- Latest upstream

* Thu Sep 26 2019 Nathan Scott <nathans@redhat.com> - 5.0.6-1
- Upstream 5.0.6 release and redis-doc updates.

* Fri Jul 26 2019 Fedora Release Engineering <releng@fedoraproject.org> - 5.0.5-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Mon Jul 15 2019 Nathan Scott <nathans@redhat.com> - 5.0.5-2
- Use the (modified) bundled jemalloc for defrag (RHBZ #1725852)

* Thu May 16 2019 Nathan Scott <nathans@redhat.com> - 5.0.5-1
- Upstream 5.0.5 release and redis-doc updates.

* Sat May 11 2019 Nathan Scott <nathans@redhat.com> - 5.0.4-2
- Obsolete redis-trib - functionality now in redis-cli(1)
- Remove old chkconfig support, all systemd platforms now

* Tue Mar 19 2019 Nathan Scott <nathans@redhat.com> - 5.0.4-1
- Upstream 5.0.4 release and redis-doc updates.
- Fix sentinel.conf logfile line addition.

* Sat Feb 02 2019 Fedora Release Engineering <releng@fedoraproject.org> - 5.0.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Thu Dec 13 2018 Nathan Scott <nathans@redhat.com> - 5.0.3-1
- Upstream 5.0.3 release and redis-doc updates.

* Fri Nov 23 2018 Nathan Scott <nathans@redhat.com> - 5.0.2-1
- Upstream 5.0.2 release and redis-doc updates.

* Thu Nov 08 2018 Nathan Scott <nathans@redhat.com> - 5.0.1-1
- Upstream 5.0.1 release.

* Thu Oct 18 2018 Nathan Scott <nathans@redhat.com> - 5.0.0-1
- Update systemd service files for network-online requirement
- Upstream 5.0.0 release.

* Thu Aug 09 2018 Nathan Scott <nathans@redhat.com> - 4.0.11-1
- Drop the pandoc build dependency, install only markdown.
- Upstream 4.0.11 release.

* Sat Jul 14 2018 Fedora Release Engineering <releng@fedoraproject.org> - 4.0.10-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Mon Jun 25 2018 Remi Collet <rcollet@redhat.com> - 4.0.10-2
- fix License (BSD and MIT)
- add bundled libraries licences
- add information about bundled lzf

* Thu Jun 14 2018 Nathan Scott <nathans@redhat.com> - 4.0.10-1
- Upstream 4.0.10 release.

* Tue Mar 27 2018 Nathan Scott <nathans@redhat.com> - 4.0.9-1
- Upstream 4.0.9 release.

* Fri Feb 09 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 4.0.8-2
- Escape macros in %%changelog

* Wed Feb  7 2018 Nathan Scott <nathans@redhat.com> - 4.0.8-1
- Upstream 4.0.8 release.

* Wed Jan 31 2018 Nathan Scott <nathans@redhat.com> - 4.0.7-1
- Upstream 4.0.7 release.

* Thu Dec  7 2017 Nathan Scott <nathans@redhat.com> - 4.0.6-1
- Upstream 4.0.6 release.

* Fri Dec  1 2017 Remi Collet <remi@remirepo.net> - 4.0.5-1
- Redis 4.0.5 - Released Thu Dec 1 16:03:32 CET 2017
- Upgrade urgency CRITICAL: Redis 4.0.4 fix for PSYNC2 was broken,
  causing the slave to crash when receiving an RDB file from the
  master that contained a duplicated Lua script.

* Fri Dec 01 2017 Nathan Scott <nathans@redhat.com> - 4.0.4-1
- Upstream 4.0.4 release.
- Update to current upstream redis-doc also.
- Fix man page issues (RHBZ #1513594 and RHBZ #1515417).

* Thu Nov 30 2017 Remi Collet <remi@remirepo.net> - 4.0.3-1
- Redis 4.0.3
- fix ownership of /usr/share/doc/redis
- use make_flags for test to avoid rebuild and failure
- fix rpm macro location on EL-6
- add /var/run/redis on EL-6
- add spec file license header
- drop duplicated documentation from main package
- keep man in main page

* Fri Nov 17 2017 Nathan Scott <nathans@redhat.com> - 4.0.2-2
- Install the base modules directories, owned by the main package.

* Tue Oct 31 2017 Nathan Scott <nathans@redhat.com> - 4.0.2-1
- Upstream 4.0.2 release.  (RHBZ #1389592)
- Add redis-devel for loadable module development.
- Add redis-doc for man pages and detailed documentation.
- Provide redis-check-aof as a symlink to redis-server also now.

* Tue Sep 26 2017 Nathan Scott <nathans@redhat.com> - 3.2.11-1
- Upstream 3.2.11 bug-fix-only release
- Switch to using Type=notify for Redis systemd services (RHBZ #1172841)
- Add Provides:bundled hiredis, linenoise, lua-libs clauses (RHBZ #788500)

* Mon Aug 14 2017 Nathan Scott <nathans@redhat.com> - 3.2.10-2
- Add redis-trib based on patch from Sebastian Saletnik.  (RHBZ #1215654)

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 3.2.9-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Mon Jul 31 2017 Nathan Scott <nathans@redhat.com> - 3.2.10-1
- Upstream 3.2.10 release
- Ensure both the redis and redis-sentinel service files set correct perms
- Dropped systemd tmpfiles source, handled directly in systemd service files

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 3.2.9-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Mon May 29 2017 Nathan Scott <nathans@redhat.com> - 3.2.9-1
- Upstream 3.2.9
- Add RuntimeDirectory=redis to systemd unit file (RHBZ #1454700)
- Mark rundir as %%ghost since it may disappear (tmpfs - #1454700)
- Fix a shutdown failure with Unix domain sockets (RHBZ #1444988)

* Mon Feb 20 2017 Haïkel Guémar <hguemar@fedoraproject.org> - 3.2.8-1
- Upstream 3.2.8
- bugfix for #3796 (MIGRATE could cause server crash  after socket error)

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 3.2.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Sat Feb  4 2017 Haïkel Guémar <hguemar@fedoraproject.org> - 3.2.7-1
- Upstream 3.2.7 (important security fix)

* Sat Nov 05 2016 Alan Pevec <apevec AT redhat.com> - 3.2.4-2
- Install tmpfiles and /run/redis for legacy configurations

* Mon Sep 26 2016 Haïkel Guémar <hguemar@fedoraproject.org> - 3.2.4-1
- Upstream 3.2.4
- Fix buffer overlow (TALOS-2016-0206)

* Wed Sep 14 2016 Remi Collet <remi@fedoraproject.org> - 3.2.3-2
- add missing man pages #1374577
  using patch from https://github.com/redis/redis/pull/3491
- data and configuration should not be publicly readable #1374700
- remove /var/run/redis with systemd #1374728
- provide redis-check-rdb as a symlink to redis-server #1374736
  using patch from https://github.com/redis/redis/pull/3494
- move redis-shutdown to libexec

* Thu Aug  4 2016 Haïkel Guémar <hguemar@fedoraproject.org> - 3.2.3-1
- Upstream 3.2.3
- Security fix for CVE-2013-7458 (redis-cli history world readable)
- RHBZ#1363670 RHBZ#1363671

* Mon Feb  8 2016 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.6-3
- Fix redis-shutdown to handle password-protected instances shutdown

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.6-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Sat Dec 19 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.6-1
- Upstream 3.0.6 (RHBZ#1272281)

* Fri Oct 16 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.5-1
- Upstream 3.0.5
- Fix slave/master replication hanging forever in certain case

* Mon Sep 07 2015 Christopher Meng <rpm@cicku.me> - 3.0.4-1
- Update to 3.0.4

* Sun Aug 30 2015 Christopher Meng <rpm@cicku.me> - 3.0.3-2
- Rebuilt for jemalloc 4.0.0

* Tue Jul 21 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.3-1
- Upstream 3.0.3

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.0.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu Jun 04 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.2-1
- Upstream 3.0.2 (RHBZ #1228245)
- Fix Lua sandbox escape and arbitrary code execution (RHBZ #1228331)

* Sat May 09 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.1-1
- Upstream 3.0.1 (RHBZ #1208322)

* Tue Apr 14 2015 Remi Collet <remi@fedoraproject.org> - 3.0.0-2
- rotate /var/log/redis/sentinel.log

* Thu Apr  2 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.0-1
- Upstream 3.0.0 (RHBZ #1208322)

* Thu Mar 26 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.19-2
- Fix redis-shutdown on multiple NIC setup (RHBZ #1201237)

* Fri Feb 27 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.19-1
- Upstream 2.8.19 (RHBZ #1175232)
- Fix permissions for tmpfiles (RHBZ #1182913)
- Add limits config files
- Spec cleanups

* Fri Dec 05 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.18-1
- Upstream 2.8.18
- Rebased patches

* Sat Sep 20 2014 Remi Collet <remi@fedoraproject.org> - 2.8.17-1
- Upstream 2.8.17
- fix redis-sentinel service unit file for systemd
- fix redis-shutdown for sentinel
- also use redis-shutdown in init scripts

* Wed Sep 17 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.15-2
- Minor fix to redis-shutdown (from Remi Collet)

* Sat Sep 13 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.15-1
- Upstream 2.8.15 (critical bugfix for sentinel)
- Fix to sentinel systemd service and configuration (thanks Remi)
- Refresh patch management

* Thu Sep 11 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.14-2
- Cleanup spec
- Fix shutdown for redis-{server,sentinel}
- Backport fixes from Remi Collet repository (ie: sentinel working)

* Thu Sep 11 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.14-1
- Upstream 2.8.14 (RHBZ #1136287)
- Bugfix for lua scripting users (server crash)
- Refresh patches
- backport spec from EPEL7 (thanks Warren)

* Wed Jul 16 2014 Christopher Meng <rpm@cicku.me> - 2.8.13-1
- Update to 2.8.13

* Tue Jun 24 2014 Christopher Meng <rpm@cicku.me> - 2.8.12-1
- Update to 2.8.12

* Wed Jun 18 2014 Christopher Meng <rpm@cicku.me> - 2.8.11-1
- Update to 2.8.11

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.16-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Fri Sep 06 2013 Fabian Deutsch <fabian.deutsch@gmx.de> - 2.6.16-1
- Update to 2.6.16
- Fix rhbz#973151
- Fix rhbz#656683
- Fix rhbz#977357 (Jan Vcelak <jvcelak@fedoraproject.org>)

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.13-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Jul 23 2013 Peter Robinson <pbrobinson@fedoraproject.org> 2.6.13-4
- ARM has gperftools

* Wed Jun 19 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-3
- Modify jemalloc patch for s390 compatibility (Thanks sharkcz)

* Fri Jun 07 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-2
- Unbundle jemalloc

* Fri Jun 07 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-1
- Add compile PIE flag (rhbz#955459)
- Update to redis 2.6.13 (rhbz#820919)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Thu Dec 27 2012 Silas Sewell <silas@sewell.org> - 2.6.7-1
- Update to redis 2.6.7

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.4.15-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sun Jul 08 2012 Silas Sewell <silas@sewell.org> - 2.4.15-2
- Remove TODO from docs

* Sun Jul 08 2012 Silas Sewell <silas@sewell.org> - 2.4.15-1
- Update to redis 2.4.15

* Sat May 19 2012 Silas Sewell <silas@sewell.org> - 2.4.13-1
- Update to redis 2.4.13

* Sat Mar 31 2012 Silas Sewell <silas@sewell.org> - 2.4.10-1
- Update to redis 2.4.10

* Fri Feb 24 2012 Silas Sewell <silas@sewell.org> - 2.4.8-1
- Update to redis 2.4.8

* Sat Feb 04 2012 Silas Sewell <silas@sewell.org> - 2.4.7-1
- Update to redis 2.4.7

* Wed Feb 01 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-4
- Fixed a typo in the spec

* Tue Jan 31 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-3
- Fix .service file, to match config (Type=simple).

* Tue Jan 31 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-2
- Fix .service file, credits go to Timon.

* Thu Jan 12 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-1
- Update to 2.4.6
- systemd unit file added
- Compiler flags changed to compile 2.4.6
- Remove doc/ and Changelog

* Sun Jul 24 2011 Silas Sewell <silas@sewell.org> - 2.2.12-1
- Update to redis 2.2.12

* Fri May 06 2011 Dan Horák <dan[at]danny.cz> - 2.2.5-2
- google-perftools exists only on selected architectures

* Sat Apr 23 2011 Silas Sewell <silas@sewell.ch> - 2.2.5-1
- Update to redis 2.2.5

* Sat Mar 26 2011 Silas Sewell <silas@sewell.ch> - 2.2.2-1
- Update to redis 2.2.2

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.4-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sun Dec 19 2010 Silas Sewell <silas@sewell.ch> - 2.0.4-1
- Update to redis 2.0.4

* Tue Oct 19 2010 Silas Sewell <silas@sewell.ch> - 2.0.3-1
- Update to redis 2.0.3

* Fri Oct 08 2010 Silas Sewell <silas@sewell.ch> - 2.0.2-1
- Update to redis 2.0.2
- Disable checks section for el5

* Sat Sep 11 2010 Silas Sewell <silas@sewell.ch> - 2.0.1-1
- Update to redis 2.0.1

* Sat Sep 04 2010 Silas Sewell <silas@sewell.ch> - 2.0.0-1
- Update to redis 2.0.0

* Thu Sep 02 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-3
- Add Fedora build flags
- Send all scriplet output to /dev/null
- Remove debugging flags
- Add redis.conf check to init script

* Mon Aug 16 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-2
- Don't compress man pages
- Use patch to fix redis.conf

* Tue Jul 06 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-1
- Initial package
