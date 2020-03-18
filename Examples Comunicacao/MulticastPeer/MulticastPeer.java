import java.net.*;
import java.io.*;
import java.util.Scanner;  // Import the Scanner class
public class MulticastPeer{
    public static void main(String args[])
		throws InterruptedException { 
		// args give message contents and destination multicast group (e.g. "228.5.6.7")
		MulticastSocket s =null;
		Scanner input = new Scanner(System.in);
		try {
			System.out.println("inicio: ");
			InetAddress group = InetAddress.getByName(args[0]);
			s = new MulticastSocket(6789);
			s.joinGroup(group);
			MulticastListener listener = new MulticastListener(s);
			while (!s.isClosed())
			{
				System.out.println("Message to be sent: ");
				String userInput = input.nextLine();
				if (userInput.equals("Sair"))
				{
					s.leaveGroup(group);
					System.exit(0);
				}
				byte [] m = userInput.getBytes();
				DatagramPacket messageOut = new DatagramPacket(m, m.length, group, 6789);
				s.send(messageOut);
				Thread.sleep(100);
			}		
		}catch (SocketException e){System.out.println("Socket: " + e.getMessage());
		}catch (IOException e){System.out.println("IO: " + e.getMessage());
		}finally {if((s != null) && !s.isClosed()) s.close();}
	}
}

class MulticastListener extends Thread  {
	MulticastSocket socket;
	public MulticastListener(MulticastSocket s) {
		socket = s;
		this.start();
	}

	public void run() {
		while (!socket.isClosed()) {
			try{
				byte[] buffer = new byte[1000];
				DatagramPacket messageIn = new DatagramPacket(buffer, buffer.length);
				socket.receive(messageIn);
				System.out.println("Received:" + new String(messageIn.getData()));
				// Arrays.fill(buffer, (byte)0);
			}catch (SocketException e) {
				System.out.println("Socket: " + e.getMessage());
				if((socket != null) && !socket.isClosed())
					socket.close();
			}catch (IOException e) {
				System.out.println("IO: " + e.getMessage());
			}
		}
	}
}