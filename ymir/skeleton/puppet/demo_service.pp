# puppet/demo_service.pp
#
#
#

# standard exec path
Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }

package {['ruby-dev', 'gem']: ensure => present }

file { '/etc/motd':
  ensure  => file,
  content => template('ymir/motd.erb'),
}

package {'supervisor': ensure => present }
service { 'supervisor':
  ensure => 'running',
  enable => true, }
