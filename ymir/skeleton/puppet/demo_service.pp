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

file{'/etc/supervisor/supervisord.conf':
  ensure  => present,
  notify  => Service['supervisor'],
  owner   => 'root',
  require => Package['supervisor'],
  content => template('ymir/supervisord.conf')}->
file {'/etc/supervisor/conf.d':
  ensure  => 'directory',
  recurse => true,
  purge   => true,
}->
file{'/etc/supervisor/conf.d/example.conf':
  ensure  => present,
  owner   => 'root',
  content => template('ymir/example.conf')}
