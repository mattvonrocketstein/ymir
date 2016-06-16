#
# puppet/demo_service.pp
#

# standard exec path
Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }

# demonstrates installing a system package
package {['tree',]: ensure => present }

# demonstrates copy/render for a puppet template, filled in with ymir variables
file { '/tmp/tmp_file_puppet':
  ensure  => file,
  content => template('ymir/tmp_file'),
}

# demonstrates using ymir variables together with an exec{}
exec { 'tag-motd-with-puppet':
  command => "printf '\npuppet-variable passed via ymir:\n  puppet_variable=${puppet_variable}\n\n' >> /etc/motd",
  unless => "cat motd|grep ${puppet_variable}"
}
