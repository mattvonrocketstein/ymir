#
# puppet/modules/ymir/install_librarian.pp
#
# Install the puppet librarian so it can bootstrap the
# dependencies mentioned in puppet/metadata.json
Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }
package { 'gem': ensure=>present }
package {'ruby-dev': ensure=>present }
exec { 'install-puppet-librarian':
  command  => 'gem install librarian-puppet',
  unless   => 'gem list | grep -c librarian-puppet'
}
