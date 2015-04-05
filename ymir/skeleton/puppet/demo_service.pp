# puppet/demo_service.pp
#
#
#

# standard exec path
Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }

package {['ruby-dev', 'gem']: ensure => present }

file { '/etc/motd':
  ensure  => file,
  content => template('ymir/cache_motd.erb'),
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
file { '/etc/supervisor/conf.d':
  ensure  => directory,
  require => Package['supervisor'],
  source  => 'puppet:///modules/ymir/supervisor.d',
  recurse => true,
  notify  => Service['supervisor']
}
