#
# puppet/modules/ymir/log_dirs.pp
#
#   create logging directories used by supervisor, etc
#

# standard exec path
Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }

file { '/opt/ymir/':
  ensure  => directory,
  recurse => true,
}

file { '/opt/ymir/logs':
  ensure  => directory,
  recurse => true,
  require => File['/opt/ymir']
}

exec { 'writable-ymir-logdir':
  command => 'chmod uog+rwx /opt/ymir/logs',
  require => File['/opt/ymir/logs']
}
